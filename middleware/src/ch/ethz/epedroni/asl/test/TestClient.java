package ch.ethz.epedroni.asl.test;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;

import ch.ethz.epedroni.asl.middleware.Middleware;

/**
 * This is a dummy client that generates hardcoded requests for testing purposes.
 * It uses a blocking socket channel for simplicity.
 * 
 * @author Eduardo Pedroni
 *
 */
public class TestClient {
	/**
	 * The middleware's port.
	 */
	private static final int PORT = 11212;
	/**
	 * A byte buffer used for writing requests and reading responses.
	 */
	private static ByteBuffer byteBuffer = ByteBuffer.allocateDirect(Middleware.BUFFER_SIZE);
	/**
	 * A socket channel to communicate with the server.
	 */
	private static SocketChannel socketChannel;
	
	public static void main(String... args) throws IOException {
		System.out.println("Starting test client...");
		socketChannel = SocketChannel.open(new InetSocketAddress("127.0.0.1", PORT));
		socketChannel.configureBlocking(true);
		
		// for reading stdin
		BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
		
		System.out.println("Connected to server, entering main loop");
		while (socketChannel.isOpen()) {
			System.out.print("> ");
			switch(reader.readLine()) {
			case "set":
				sendRequest("set 98r1rjnc04 0 0 128\r\n"
						+ "K2hs73W6DsmdnkU.MHOn6.Usp9KLp-B71s.9vUF6K0j6kB44TSrZQKPDTkYHjjOkaMtTq7a97HFrTJwwmlTA3tOXbwoIeA0CXufL-DU6Vjxy1rsnbJxeAJ9lEx1s622d\r\n");
				break;
			case "get":
				sendRequest("get 39428rnu48\r\n");
				break;
			case "delete":
				sendRequest("delete j0nidsv791h\r\n");
				break;
			case "exit":
				System.out.println("Closing socket");
				socketChannel.close();
				break;
			default:
				break;
			}
		}		
		System.out.println("Finished");
	}
	
	/**
	 * Sends a request through the socket channel and prints a
	 * response to stdout.
	 * 
	 * @param request the request text to send
	 * @throws IOException if something bad happens with the socket channel
	 */
	private static void sendRequest(String request) throws IOException {
		byteBuffer.clear();
		byteBuffer.put(request.getBytes());
		byteBuffer.flip();

		System.out.println("Sending out request, key: " + request.split(" ")[1].trim());
		socketChannel.write(byteBuffer);

		byteBuffer.clear();
		socketChannel.read(byteBuffer);
		byteBuffer.flip();

		byte[] bytes = new byte[byteBuffer.remaining()];
		byteBuffer.get(bytes);
		System.out.println("Received response: " + new String(bytes));
	}
}
