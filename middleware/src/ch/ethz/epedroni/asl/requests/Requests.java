package ch.ethz.epedroni.asl.requests;

import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.util.concurrent.LinkedBlockingDeque;

/**
 * This class provides an interface to acquire new request objects via a
 * getter method. It actually makes use of a dynamically-sized pool of 
 * requests to hopefully make the GC's life easier. Statistics are also
 * logged here when requests are recycled.
 * 
 * @author Eduardo Pedroni
 *
 */
public class Requests {
	/**
	 * The different request types, for logging purposes. 
	 */
	public enum Type {
		WRITE, READ, UNKNOWN;
	}
	/**
	 * A dynamically-sized pool of {@code Request} objects is maintained
	 * here so that requests can be re-used. This enables direct allocation
	 * of buffers which theoretically improves IO speed. It should also
	 * reduce the memory footprint and hopefully reduce the impact of
	 * garbage collection runs on the overall performance of the system.
	 */
	private static LinkedBlockingDeque<Request> requestPool = new LinkedBlockingDeque<>();
	/**
	 * Used to log only one out of SAMPLE_INTERVAL requests.
	 */
	private static int writeLogCounter = 0, readLogCounter = 0;
	/**
	 * Determines how often samples should be logged.
	 */
	private static final int SAMPLE_INTERVAL = 100;
	
	/**
	 * This class cannot be instantiated.
	 */
	private Requests() {}
	
	/**
	 * Returns a request object ready to be used. <strong>The provided
	 * byte buffer should be ready for reading so it can be copied.</strong>
	 * 
	 * @param requestBytes a byte buffer containing the request bytes
	 * @param clientChannel the socket channel whence this request came
	 */
	public static Request getRequest(ByteBuffer requestBytes, 
			SocketChannel clientChannel) {
		Request r;
		// if list is empty, create a new request
		if (requestPool.isEmpty()) {
			r = new Request();
		}
		// if recycled requests are available, use one
		else {
			r = requestPool.pop();
			r.responseCount = 0;
			r.getByteBuffer().clear();
		}

		// initialise it with the provided arguments
		r.setClientChannel(clientChannel);
		r.getByteBuffer().put(requestBytes);
		r.getByteBuffer().flip();
		
		// store the key already parsed
		r.extractKey();
		r.extractType();
		
		return r;
	}
	
	/**
	 * Takes requests to be re-purposed for future use. The request should
	 * no longer be used after this method returns.
	 * 
	 * @param request the request to recycle
	 */
	public static void recycleRequest(Request request) {
		// also log the requests here, if necessary
		switch (request.getType()) {
		case READ:
			if (readLogCounter++ >= SAMPLE_INTERVAL) {
				readLogCounter = 0;
				request.log();
			}
			break;
		case WRITE:
			if (writeLogCounter++ >= SAMPLE_INTERVAL) {
				writeLogCounter = 0;
				request.log();
			}
			break;
		case UNKNOWN:
			System.out.println("Recycling request of unknown type!");
		default:
			break;
		}
		requestPool.push(request);
	}
}
