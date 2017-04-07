package ch.ethz.epedroni.asl.memcached;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.SocketChannel;
import java.util.Iterator;
import java.util.concurrent.BlockingQueue;

import ch.ethz.epedroni.asl.middleware.Middleware;
import ch.ethz.epedroni.asl.requests.Request;
import ch.ethz.epedroni.asl.requests.Requests;

/**
 * A runnable to be executed by a thread for handling write requests.
 * It dequeues requests from the specified primary server's write queue,
 * forwards them to all specified servers asynchronously and waits for all
 * responses before responding to the client. The response sent to the client
 * is only positive if all servers returned positive responses.
 * 
 * @author Eduardo Pedroni
 *
 */
public class WriteRunnable implements Runnable {
	/**
	 * An array of connections to each of the servers specified.
	 */
	private SocketChannel[] serverConnections;
	/**
	 * The request queue from which to get requests.
	 */
	private BlockingQueue<Request> requestQueue;
	/**
	 * Used to perform IO operations asynchronously.
	 */
	private Selector selector;
	/**
	 * This buffer stores the response to be sent back to client.
	 * It is modified as server responses are received.
	 */
	private ByteBuffer responseBuffer;
	/**
	 * Server responses are read into this buffer so they can be processed
	 * and potentially copied to {@code responseBuffer}.
	 */
	private ByteBuffer receiverBuffer;

	/**
	 * Instantiates a new write runnable and creates connections
	 * to the specified servers.
	 * 
	 * @param servers the servers to which the requests should be forwarded
	 * @throws IOException if it fails to connect to the servers
	 */
	public WriteRunnable(Memcached[] servers) throws IOException {
		this.selector = Selector.open();
		this.requestQueue = servers[0].getWriteQueue();
		this.serverConnections = new SocketChannel[servers.length];
		for (int i = 0; i < servers.length; i++) {
			serverConnections[i] = SocketChannel.open(servers[i].getAddress());
			serverConnections[i].configureBlocking(false);
			serverConnections[i].register(selector, SelectionKey.OP_WRITE
					| SelectionKey.OP_READ);
		}
		// direct allocation is supposedly better for long-lived IO buffers
		// http://stackoverflow.com/a/5671880/3482616
		this.responseBuffer = ByteBuffer.allocateDirect(Middleware.BUFFER_SIZE);
		this.receiverBuffer = ByteBuffer.allocateDirect(Middleware.BUFFER_SIZE);
	}

	@Override
	public void run() {
		Request request;
		Iterator<SelectionKey> selectedKeys;
		SelectionKey key;
		SocketChannel channel;
		boolean timestamp = false;

		try {
			while (selector.isOpen()) {
				request = requestQueue.take();
				request.dequeued(System.nanoTime());

				// handle one request at a time, but communicate with servers asynchronously
				while (request.responseCount < serverConnections.length) {
					selector.select();
					selectedKeys = selector.selectedKeys().iterator();

					while (selectedKeys.hasNext()) {
						key = selectedKeys.next();
						channel = (SocketChannel) key.channel();
						/*
						 * Here we:
						 * 	- write request to the selected channel if it is not already
						 *    attached to it
						 *  - rewind the request so it can be sent to other servers
						 *  - attach to key so we don't send it to this server again
						 */
						if (key.isWritable() && key.attachment() != request) {
							channel.write(request.getByteBuffer());
							if (!timestamp) {
								request.sentToServer(System.nanoTime());
								timestamp = true;
							}
							request.getByteBuffer().rewind();
							key.attach(request);
						}
						/*
						 * Here we:
						 * 	- read responses from servers
						 *  - consolidate with the currently received responses
						 *  - update request's response count
						 */
						else if (key.isReadable()) {
							receiverBuffer.clear();
							channel.read(receiverBuffer);
							// only buffer the response if it will add information we need
							if (responseBuffer.get(0) != 'N' && receiverBuffer.get(0) == 'N' 
									|| responseBuffer.remaining() == responseBuffer.capacity()) {
								receiverBuffer.flip();
								responseBuffer.clear();
								responseBuffer.put(receiverBuffer);
							}
							request.responseCount++;
						}
						selectedKeys.remove();
					}
				}
				// all responses have been received, send off and loop to next request
				request.receivedFromServer(System.nanoTime());
				responseBuffer.flip();
				request.getClientChannel().write(responseBuffer);
				request.sentToClient(System.nanoTime());
				request.success();
				
				// need to clear here so that it is guaranteed to be overwritten at least once
				responseBuffer.clear();
				timestamp = false;
				Requests.recycleRequest(request);
				
				/* 
				 * This is the price for the request pool. If we don't do this,
				 * this loop could hang on writable selections if the same request
				 * object happens to be used twice in a row.
				 * 
				 * XXX: there is probably a nicer way to handle this
				 */
				for (SelectionKey k : selector.keys()) {
					k.attach(null);
				}
			}
		} catch (InterruptedException | IOException e) {
			e.printStackTrace();
		}
	}
}
