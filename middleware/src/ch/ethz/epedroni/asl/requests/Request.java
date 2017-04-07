package ch.ethz.epedroni.asl.requests;

import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.util.logging.Level;

import ch.ethz.epedroni.asl.middleware.Middleware;
import ch.ethz.epedroni.asl.requests.Requests.Type;

/**
 * Holds information relative to a single client request. For new
 * requests use {@code Request.getRequest()}.
 * 
 * @author Eduardo Pedroni
 *
 */
public class Request {
	/**
	 * The actual bytes received from the client.
	 */
	private ByteBuffer requestBytes;
	/**
	 * The key extracted from the request.
	 */
	private byte[] key;
	/**
	 * The type extracted from the request.
	 */
	private Type type;
	/**
	 * The socket which is connected to the client.
	 */
	private SocketChannel clientChannel;
	/**
	 * Number of responses received for this request.
	 * This field is only used for write requests.
	 */
	public int responseCount = 0;
	/**
	 * Metrics timing variables. These are accessed and modified via methods.
	 */
	private long timeMiddlewareIn = 0, timeQueueIn = 0, timeServerIn = 0;
	private long timeMiddlewareOut = 0, timeQueueOut = 0, timeServerOut = 0;
	private int successFlag = 0;
	
	/**
	 * This constructor is visible only in the package as it may only be used
	 * in {@code Requests.getRequest()}.
	 */
	Request() {
		this.requestBytes = ByteBuffer.allocateDirect(Middleware.BUFFER_SIZE);
	}
	
	/**
	 * Extracts the key from the request byte buffer and assigns it to the key
	 * field as an array of bytes.
	 */
	void extractKey() {
		// the key should be the second element in every request
		int index = 1;
		
		int tokenStart = 0, tokenEnd = 0;
		while (index > 0) {
			if (requestBytes.get(tokenStart) == ' ') {
				index--;
			} else if (requestBytes.get(tokenStart) == '\r') {
				index--;
				// skip the next character, which is the \n
				tokenStart++;
			}
			tokenStart++;
			if (tokenStart >= requestBytes.limit()) return;
		}
		
		// figure out where the indexth token ends
		tokenEnd = tokenStart;
		while (requestBytes.get(tokenEnd) != ' ' && requestBytes.get(tokenEnd) != '\r') {
			tokenEnd++;
			if (tokenEnd >= requestBytes.limit()) return;
		}
		
		if (key == null || key.length != tokenEnd - tokenStart) {
			key = new byte[tokenEnd - tokenStart];
		}
		
		requestBytes.position(tokenStart);
		requestBytes.get(key, 0, key.length);
		requestBytes.rewind(); // by convention always leave the buffer in a readable state
	}
	
	/**
	 * Extracts the type of request from the request byte buffer and assigns it
	 * to the type field.
	 */
	void extractType() {
		// (s)ets and (d)eletes are write requests
		if (requestBytes.get(0) == 's' || requestBytes.get(0) == 'd') {
			type = Type.WRITE;
			
		// (g)et is a read request
		} else if (requestBytes.get(0) == 'g') {
			type = Type.READ;
			
		// if it begins with something else, we don't know it
		} else {
			type = Type.UNKNOWN;
		}
	}

	/**
	 * Sets this request's client channel to the provided socket channel.
	 * 
	 * @param socketChannel the new socket channel
	 */
	void setClientChannel(SocketChannel socketChannel) {
		this.clientChannel = socketChannel;
	}
	
	/**
	 * @return a channel connected to the client who sent the request
	 */
	public SocketChannel getClientChannel() {
		return clientChannel;
	}
	
	/**
	 * Returns a {@code ByteBuffer} containing the request bytes received so far.
	 * 
	 * @return the request buffer
	 */
	public ByteBuffer getByteBuffer() {
		return requestBytes;
	}
	
	/**
	 * @return the key of the request, already parsed
	 */
	public byte[] getKey() {
		return key;
	}
	
	/**
	 * @return the type of request
	 */
	public Type getType() {
		return type;
	}
	
	/**
	 * Sets the time when the request was first received from the client (entered the middleware).
	 * 
	 * @param time the system time in nanoseconds
	 */
	public void receivedFromClient(long time) {
		timeMiddlewareIn = time;
	}
	
	/**
	 * Sets the time when the request was finally sent back to the client (left the middleware).
	 * 
	 * @param time the system time in nanoseconds
	 */
	public void sentToClient(long time) {
		timeMiddlewareOut = time;
	}
	
	/**
	 * Sets the time when the request was added to its queue.
	 * 
	 * @param time the system time in nanoseconds
	 */
	public void enqueued(long time) {
		timeQueueIn = time;
	}
	
	/**
	 * Sets the time when the request was removed from its queue.
	 * 
	 * @param time the system time in nanoseconds
	 */
	public void dequeued(long time) {
		timeQueueOut = time;
	}
	
	/**
	 * Sets the time when the request was sent to its server.
	 * 
	 * @param time the system time in nanoseconds
	 */
	public void sentToServer(long time) {
		timeServerIn = time;
	}
	
	/**
	 * Sets the time when the request response was received from its server.
	 * 
	 * @param time the system time in nanoseconds
	 */
	public void receivedFromServer(long time) {
		timeServerOut = time;
	}
	
	/**
	 * Marks this request as successful.
	 */
	public void success() {
		successFlag = 1;
	}
	
	/**
	 * Logs this request to the statistics logger.
	 */
	public void log() {
		Middleware.TRACE_LOGGER.log(Level.INFO,
				String.format("%s,%d,%d,%d,%d,%d,%d,%d",
				type, timeMiddlewareIn, timeMiddlewareOut, timeQueueIn, timeQueueOut, timeServerIn, timeServerOut, successFlag));
	}
}
