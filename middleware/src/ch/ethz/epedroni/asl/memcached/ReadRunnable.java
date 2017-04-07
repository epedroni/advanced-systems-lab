package ch.ethz.epedroni.asl.memcached;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.util.concurrent.BlockingQueue;

import ch.ethz.epedroni.asl.requests.Request;
import ch.ethz.epedroni.asl.requests.Requests;

/**
 * A runnable to be executed by a thread for handling read requests.
 * It dequeues requests from the specified server's read queue,
 * forwards them to the server and synchronously waits for a response
 * to relay back to the client.
 * 
 * @author Eduardo Pedroni
 *
 */
public class ReadRunnable implements Runnable {
	/**
	 * A connection to the server to which the requests are to be forwarded.
	 */
	private SocketChannel serverConnection;
	/**
	 * The queue from which to get requests.
	 */
	private BlockingQueue<Request> requestQueue;

	/**
	 * Instantiates a new read runnable and creates a connection
	 * to the specified server.
	 * 
	 * @param server the server to which the requests should be forwarded
	 * @throws IOException if it fails to connect to the server
	 */
	public ReadRunnable(Memcached server) throws IOException {
		this.serverConnection = SocketChannel.open(server.getAddress());
		this.serverConnection.configureBlocking(true);
		this.requestQueue = server.getReadQueue();
	}

	@Override
	public void run() {
		Request request;
		ByteBuffer buffer;

		try {
			while (serverConnection.isOpen()) {
				// grab the next request
				request = requestQueue.take();
				request.dequeued(System.nanoTime());

				buffer = request.getByteBuffer();

				// write request to the server
				serverConnection.write(buffer);
				request.sentToServer(System.nanoTime());

				// read the response
				buffer.clear();
				serverConnection.read(buffer);
				request.receivedFromServer(System.nanoTime());

				// relay back to user
				buffer.flip();
				request.getClientChannel().write(buffer);
				request.sentToClient(System.nanoTime());
				request.success();

				Requests.recycleRequest(request);
			}
		} catch (InterruptedException | IOException e) {
			// interruptions should never happen
			e.printStackTrace();
		}
	}
}
