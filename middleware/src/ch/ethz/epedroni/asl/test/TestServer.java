package ch.ethz.epedroni.asl.test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;

import ch.ethz.epedroni.asl.middleware.Middleware;

/**
 * This is a dummy cluster of servers which listen on successive ports and
 * return "STORED\r\n" or "NOT_STORED\r\n" randomly at a 3:1 ratio.
 * 
 * @author Eduardo Pedroni
 *
 */
public class TestServer {
	/**
	 * The first server will listen on this port, every successive server on
	 * each successive port.
	 */
	private static final int STARTING_PORT = 11212;
	/**
	 * The number of servers to instantiate and run.
	 */
	private static final int SERVERS = 2;

	public static void main(String... args) throws IOException {
		System.out.println("[TestServer] Starting servers");
		for (int i = 0; i < SERVERS; i++) {
			new Thread(new Server(STARTING_PORT + i, ("s" + i))).start();
		}
	}

	/**
	 * A very basic server which listens for new clients on a specified socket
	 * and spawns threads to handle every client that connects. 
	 */
	private static class Server implements Runnable {
		/**
		 * The channel used to listen for new clients.
		 */
		private ServerSocketChannel ssc;
		/**
		 * This server's name for console prints.
		 */
		private String name;

		/**
		 * Creates a new server with an open server socket for accepting
		 * new clients.
		 * 
		 * @param port the port to listen on
		 * @param name the server's name
		 * @throws IOException if opening the server socket fails
		 */
		public Server(int port, String name) throws IOException {
			System.out.println("[" + name + "] Starting " + name + ", listening on port " + port);
			this.ssc = ServerSocketChannel.open();
			ssc.bind(new InetSocketAddress(port));
			this.name = name;
		}

		@Override
		public void run() {
			int client = 0;
			try {
				while (true) {
					System.out.println("[" + name + "] Waiting for connection");
					new Thread(new ClientRunnable(ssc.accept(), (name + "-c" + client++))).start();
					System.out.println("[" + name + "] Got client, setting off a thread");
				}
			} catch(IOException e) {
				e.printStackTrace();
			}
		}
	}

	/**
	 * A very basic client handler which reads requests from a client and
	 * send back a random response.
	 */
	private static class ClientRunnable implements Runnable {
		/**
		 * The connection to the client.
		 */
		private SocketChannel socketChannel;
		/**
		 * The client's name for console prints.
		 */
		private String name;

		/**
		 * Prepares a new client runnable to handle clients
		 * 
		 * @param socketChannel the connection to the client
		 * @param name the client's name for reference
		 * @throws IOException if setting the socket channel to blocking fails
		 */
		public ClientRunnable(SocketChannel socketChannel, String name) throws IOException {
			this.name = name;
			this.socketChannel = socketChannel;
			socketChannel.configureBlocking(true);
		}

		@Override
		public void run() {
			ByteBuffer byteBuffer = ByteBuffer.allocate(Middleware.BUFFER_SIZE);
			byte[] bytes;
			int readBytes;
			String response;
			try {
				while (socketChannel.isOpen()) {
					byteBuffer.clear();
					readBytes = socketChannel.read(byteBuffer);
					byteBuffer.flip();

					if (readBytes >= 0) {
						bytes = new byte[byteBuffer.remaining()];
						byteBuffer.get(bytes);
						System.out.println("[" + name + "] Read message from client: " + new String(bytes));
						response = getResponse();
						System.out.println("[" + name + "] Sending response: " + response);

						byteBuffer.clear();
						byteBuffer.put(response.getBytes());
						byteBuffer.flip();
						System.out.println("[" + name + "] Wrote " + socketChannel.write(byteBuffer) + " bytes");
					} else {
						System.out.println("[" + name + "] Client has disconnected, exiting");
						socketChannel.close();
					}
				}
			} catch(IOException e) {
				e.printStackTrace();
			}
		}
		
		/**
		 * Generates a random response:<br>
		 * 	- "STORED\r\n" 3 out of 4 times;<br>
		 * 	- "NOT_STORED\r\n" 1 out of 4 times.<br>
		 * 
		 * @return the generated response
		 */
		private String getResponse() {
			if (Math.random() > 0.75) {
				return "NOT_STORED\r\n";
			} else {
				return "STORED\r\n";
			}
		}

	}
}
