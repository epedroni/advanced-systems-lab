package ch.ethz.epedroni.asl.middleware;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.ClosedChannelException;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.logging.Logger;

import ch.ethz.epedroni.asl.log.MiddlewareLog;
import ch.ethz.epedroni.asl.memcached.Memcached;
import ch.ethz.epedroni.asl.memcached.ReadRunnable;
import ch.ethz.epedroni.asl.memcached.WriteRunnable;
import ch.ethz.epedroni.asl.requests.Request;
import ch.ethz.epedroni.asl.requests.Requests;

/**
 * Top-level class for the middleware. To run it, create an instance of this
 * class and call {@code run}.
 * 
 * @author Eduardo Pedroni
 *
 */
public class Middleware {
	/**
	 * IP address this middleware is listening on.
	 */
	private String ip;
	/**
	 * Port this middleware is listening on.
	 */
	private int port;
	/**
	 * List of memcached addresses to connect to.
	 */
	private List<String> mcAddresses;
	/**
	 * Number of threads to use in the read thread pool.
	 */
	private int numThreadsPTP;
	/**
	 * Number of memcached instances to which to forward each write request.
	 * Should not be greater than {@code mcAddresses.size()}.
	 */
	private int writeToCount;
	/**
	 * The size of all byte buffers used in the middleware.
	 */
	public static final int BUFFER_SIZE = 1200;
	/**
	 * This logger is used for statistics and prints to a file.
	 */
	public static Logger TRACE_LOGGER;
	/**
	 * This selector asynchronously handles incoming client requests.
	 */
	private Selector clientSelector;
	/**
	 * This channel listens for new client connections.
	 */
	private	ServerSocketChannel serverSocket;
	/**
	 * This holds all memcached instances with which we communicate.
	 */
	private Memcached[] servers;
	/**
	 * A long-lived byte buffer which is directly allocated to improve
	 * IO performance. Client requests are read into this buffer.
	 */
	private ByteBuffer byteBuffer = ByteBuffer.allocateDirect(BUFFER_SIZE);

	/**
	 * Create a new instance of the middleware with the specified parameters.
	 * 
	 * @param myIp the IP address to listen on
	 * @param myPort the port number to listen on
	 * @param mcAddresses a list of memcached addresses to connect to
	 * @param numThreadsPTP number of threads in read thread pool
	 * @param writeToCount number of servers to forward write requests to
	 */
	public Middleware(String myIp, int myPort, List<String> mcAddresses, 
			int numThreadsPTP, int writeToCount) {
		this.ip = myIp;
		System.out.println("IP: " + ip);
		this.port = myPort;
		System.out.println("Port: " + port);
		this.mcAddresses = mcAddresses;
		for (String s : mcAddresses) {
			System.out.println("Memcached: " + s);
		}
		this.numThreadsPTP = numThreadsPTP;
		System.out.println("Read thread pool size: " + numThreadsPTP);
		this.writeToCount = writeToCount;
		System.out.println("Write replication factor: " + writeToCount);
	}

	/**
	 * Starts off this middleware: create read and write threads, create
	 * server socket channel, connect to memcached instances and get ready
	 * to handle incoming requests.
	 * 
	 * @throws IOException if anything goes wrong with the network sockets
	 */
	public void run() throws IOException {
		TRACE_LOGGER = MiddlewareLog.getTraceLogger();		
		createServers();
		createReadThreads();
		createWriteThreads();
		createServerSocket();
		
		System.out.println("Entering main loop");		
		while(clientSelector.isOpen()) {
			clientSelector.select();
			handleSelections(clientSelector.selectedKeys());
		}
	}
	
	/**
	 * Create servers from specified addresses.
	 */
	private void createServers() {
		System.out.println("Instantiating memcached server objects");
		servers = new Memcached[mcAddresses.size()];
		for (int i = 0; i < mcAddresses.size(); i++) {
			servers[i] = new Memcached(mcAddresses.get(i).split(":")[0], 
					Integer.parseInt(mcAddresses.get(i).split(":")[1]));
		}
	}

	/**
	 * Create numThreadsPTP reader threads for each server.
	 * 
	 * @throws IOException if it fails to connect to the servers
	 */
	private void createReadThreads() throws IOException {
		System.out.println("Instantiating read threads");
		for (int i = 0; i < mcAddresses.size(); i++) {
			for (int t = 0; t < numThreadsPTP; t++) {
				new Thread(new ReadRunnable(servers[i])).start();
			}
		}
	}

	/**
	 * Give each write runnable an array of size writeToCount with the
	 * servers it should replicate to, in order (0 is the primary).
	 * To accomplish that, this function creates copies of the original
	 * array, cycling by one each time.
	 * 
	 * NB: writeToCount should never exceed the number of servers.
	 * 
	 * @throws IOException if it fails to connect with the servers
	 */
	private void createWriteThreads() throws IOException {
		System.out.println("Instantiating write threads");
		Memcached[] replicationServers = Arrays.copyOf(servers, servers.length);
		for (int i = 0; i < servers.length; i++) {
			new Thread(new WriteRunnable(Arrays.copyOfRange(replicationServers,
					0, writeToCount))).start();

			// cycle once
			replicationServers = Arrays.copyOf(replicationServers, 
					replicationServers.length + 1);
			replicationServers[replicationServers.length - 1] = replicationServers[0];
			replicationServers = Arrays.copyOfRange(replicationServers, 1, 
					replicationServers.length);
		}
	}
	
	/**
	 * Creates a server socket listening on the specified IP and port and registers
	 * it on the selector.
	 * 
	 * @throws IOException if the server socket cannot be created
	 * @throws ClosedChannelException if the socket cannot be registered on the selector
	 */
	private void createServerSocket() throws IOException, ClosedChannelException {
		System.out.println("Instantiating and binding server socket channel");
		serverSocket = ServerSocketChannel.open();
		serverSocket.bind(new InetSocketAddress(ip, port));
		serverSocket.configureBlocking(false);
		clientSelector = Selector.open();
		serverSocket.register(clientSelector, SelectionKey.OP_ACCEPT);
	}
	
	/**
	 * Handle a set of selection keys returned by {@code clientSelector.select()}.
	 * This method accepts new client connections if the key was acceptable,
	 * but also handles existing clients' requests.
	 * 
	 * @param selectedKeys the set of selected keys from the selector
	 * @throws IOException if networking errors occur
	 */
	private void handleSelections(Set<SelectionKey> selectedKeys) throws IOException {
		Iterator<SelectionKey> keyIterator = selectedKeys.iterator();
		SelectionKey key;
		
		while (keyIterator.hasNext()) {
			key = keyIterator.next();
			if (key.isAcceptable()) {
				handleAcceptable();
			} else if (key.isReadable()) {
				handleReadable(key);
			} else {
				System.out.println("Ignoring selected key " + key 
						+ " with unexpected interest " + key.interestOps());
			}
			keyIterator.remove();
		}
	}

	/**
	 * Receiving requests from connected clients:<br>
	 * 	- read bytes into the buffer and flip<br>
	 * 	- identify request type<br>
	 * 	- acquire a request object<br>
	 * 	- based on hash, add to correct queue
	 * 
	 * @param key the selected key
	 * @throws IOException if something is wrong with the client socket
	 */
	private void handleReadable(SelectionKey key) throws IOException {
		SocketChannel channel;
		Request request;
		long timeStamp;
		
		channel = (SocketChannel) key.channel();
	
		byteBuffer.clear();
		int readBytes = channel.read(byteBuffer);
		timeStamp = System.nanoTime();
		
		if (readBytes >= 0) {
			byteBuffer.flip();

			// requests cannot be explicitly instantiated
			request = Requests.getRequest(byteBuffer, channel);
			request.receivedFromClient(timeStamp);
			
			// send to the correct server - it'll handle it according to type
			servers[distributeRequest(request)].enqueueRequest(request);
		} else {
			System.out.println(key + " appears to have "
					+ "disconnected, removing key");
			key.cancel();
			channel.close();
		}
	}

	/**
	 * Accepts a new connection, sets to non-blocking and registers
	 * on the selector.
	 * 
	 * @throws IOException if something is wrong with the channels
	 * @throws ClosedChannelException if the server socket channel is closed
	 */
	private void handleAcceptable() throws IOException, ClosedChannelException {
		SocketChannel channel;
		System.out.println("Accepting new client connection");
		channel = serverSocket.accept();
		// serverSocket is non-blocking, so accept() could return null
		if (channel != null) {
			channel.configureBlocking(false);
			System.out.println("Registered key: " + 
			channel.register(clientSelector, SelectionKey.OP_READ));
		}
	}
	
	/**
	 * Given a request, this method returns the index of the server to
	 * which it should be sent by hashing its key. 
	 * 
	 * @param request the request to process
	 * @return the destination server index
	 */
	private int distributeRequest(Request request) {
		// TODO: investigate different hash functions - MD5?
		int hash = Arrays.hashCode(request.getKey());
		int server = Math.abs(hash % servers.length);
		return server;
	}
}