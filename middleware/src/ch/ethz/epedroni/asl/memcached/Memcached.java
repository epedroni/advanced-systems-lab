package ch.ethz.epedroni.asl.memcached;

import java.net.InetSocketAddress;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

import ch.ethz.epedroni.asl.requests.Request;
import ch.ethz.epedroni.asl.requests.Requests;

/**
 * Represents an instance of memcached running elsewhere.
 * 
 * @author Eduardo Pedroni
 *
 */
public class Memcached {
	/**
	 * This memcached's address.
	 */
	private InetSocketAddress address;
	/**
	 * The queue of read requests bound for this memcached.
	 */
	private BlockingQueue<Request> readQueue;
	/**
	 * The queue of write requests bound for this memcached.
	 */
	private BlockingQueue<Request> writeQueue;
		
	/**
	 * Stores this memcached's IP and port and initialises the
	 * internal queues.
	 * 
	 * @param ip memcached's IP address
	 * @param port memcached's port
	 */
	public Memcached(String ip, int port) {
		this.address = new InetSocketAddress(ip, port);
		this.readQueue = new LinkedBlockingQueue<>();
		this.writeQueue = new LinkedBlockingQueue<>();
	}

	/**
	 * @return this memcached's network address
	 */
	public InetSocketAddress getAddress() {
		return address;
	}
	
	/**
	 * Enqueue the provided request to the appropriate queue depending
	 * on its type.
	 * 
	 * @param request the request to enqueue
	 */
	public void enqueueRequest(Request request) {
		switch (request.getType()) {
		case READ:
			readQueue.add(request);
			request.enqueued(System.nanoTime());
			break;
		case WRITE:
			writeQueue.add(request);
			request.enqueued(System.nanoTime());
			break;
		default:
			// if this happens, the request is not marked successful
			byte[] requestDump = new byte[request.getByteBuffer().remaining()];
			request.getByteBuffer().get(requestDump);
			System.out.println("Unknown operation, request dump: "
			+ new String(requestDump));
			Requests.recycleRequest(request);
			break;
		}
	}
	
	/**
	 * @return this memcached's queue for read requests (get)
	 */
	public BlockingQueue<Request> getReadQueue() {
		return readQueue;
	}

	/**
	 * @return this memcached's queue for write requests (set and delete)
	 */
	public BlockingQueue<Request> getWriteQueue() {
		return writeQueue;
	}
}
