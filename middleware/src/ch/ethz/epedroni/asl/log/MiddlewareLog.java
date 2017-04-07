package ch.ethz.epedroni.asl.log;

import java.io.IOException;
import java.util.logging.FileHandler;
import java.util.logging.Formatter;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

/**
 * Contains some utility methods for providing uniformly-configured loggers for
 * the entire application. Currently only really used for the trace.
 * 
 * @author Eduardo Pedroni
 *
 */
public class MiddlewareLog {

	/**
	 * Configures and returns the trace logger.
	 * 
	 * @return the trace logger
	 * @throws IOException if there are IO problems opening the files.
	 * @throws SecurityException if a security manager exists and if the caller does not have LoggingPermission("control")
	 */
	public static Logger getTraceLogger() throws SecurityException, IOException {
		Logger logger = Logger.getLogger("statistics");
		logger.setLevel(Level.ALL);
		
		FileHandler handler = new FileHandler("middleware.log");
		handler.setFormatter(new Formatter() {
			@Override
			public String format(LogRecord record) {
				return record.getMessage() + "\n";
			}
		});
		handler.setLevel(Level.ALL);
		logger.addHandler(handler);
		// do not print to stderr or any other silliness 
		logger.setUseParentHandlers(false);
		logger.log(Level.INFO, "# type,Tmiddleware_in,Tmiddleware_out,Tqueue_in,Tqueue_out,Tserver_in,Tserver_out,Fsuccess");
		return logger;
	}
}
