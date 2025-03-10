# Import required modules - advise user retry on fail
try:
    import socket
    import threading
    import json
    import logging
    from datetime import datetime
except ImportError:
    raise ImportError('Failed to start, close and retry')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ALLOWED_IPS = ['127.0.0.1', '192.168.1.100']  # Add allowed client IPs
MAX_CONNECTIONS_PER_IP = 2  # Maximum number of connections allowed per IP
client_connections = {}  # Dictionary to track connections per IP

clients = []  # List to store connected client sockets
clients_lock = threading.Lock()  # Lock to prevent concurrent modifications


# Handles chat client connection - responsible for receiving and sending messages to and from clients.
def handle_client(client_socket, address):
    try:
        logging.info(f"Accepted connection from {address}")
        client_ip = address[0]
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        client_name = client_socket.recv(1024).decode().strip()

        if not client_name or len(client_name) > 30:
            logging.warning(f"Invalid name received from {address}. Disconnecting...")
            client_socket.close()
            return

        # Notify all clients about the new user
        broadcastData = {'timestamp': timestamp, 'name': 'SERVER', 'text': f"{client_name} has joined the chat"}
        broadcast(broadcastData, client_socket)

        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break  # Client disconnected
                
                # Process incoming message
                message = json.loads(data.decode())

                # Validate message structure
                if not isinstance(message, dict) or 'text' not in message:
                    logging.warning(f"Invalid message format from {client_name}, ignoring.")
                    continue
                
                # Limit message length (avoid spam attacks)
                if len(message['text']) > 500:
                    logging.warning(f"Message too long from {client_name}, ignoring.")
                    continue

                # Remove any harmful characters (basic input sanitation)
                message['text'] = message['text'].replace("<script>", "").replace("</script>", "")

                # Append timestamp and sender name
                message['timestamp'] = datetime.now().strftime('%H:%M:%S')
                message['name'] = client_name

                logging.info(f"(Debugging) {message['timestamp']} - {client_name}: {message['text']}")

                # Broadcast the message
                broadcast(message, client_socket)

            except (json.JSONDecodeError, ValueError):
                logging.warning(f"Malformed message from {client_name}, ignoring.")
                continue

    except ConnectionResetError:
        logging.warning(f"Connection lost with {address}")

    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")

    finally:
        # Client disconnect cleanup
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)

        # Decrement connection count for this IP
        client_connections[client_ip] = max(0, client_connections.get(client_ip, 0) - 1)

        client_socket.close()
        logging.info(f"{client_name} disconnected")


# Broadcasts message to all connected clients except sender
def broadcast(message, sender_socket):
    with clients_lock:
        for client in clients:
            if client != sender_socket:
                try:
                    client.send(json.dumps(message).encode())
                except:
                    logging.warning("Failed to send message, removing client.")
                    clients.remove(client)


# Creates socket, binds to IP address and port, and listens for incoming connections.
def create_socket_bind(host='0.0.0.0', port=8888):
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allows immediate reuse of port after crash
    server_socket.bind((host, port))
    server_socket.listen(5)

    logging.info(f'Server is listening on {host}:{port}')

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            client_ip = client_address[0]

            # Restrict unauthorized IPs
            if client_ip not in ALLOWED_IPS:
                logging.warning(f"Unauthorized connection attempt from {client_ip}")
                client_socket.close()
                continue

            # Limit connections per IP
            client_connections[client_ip] = client_connections.get(client_ip, 0) + 1
            if client_connections[client_ip] > MAX_CONNECTIONS_PER_IP:
                logging.warning(f"Too many connections from {client_ip}, rejecting.")
                client_socket.close()
                client_connections[client_ip] -= 1  # Reduce count
                continue

            with clients_lock:
                clients.append(client_socket)

            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

    except KeyboardInterrupt:
        logging.info("Shutting down server...")

    finally:
        handle_cleanup()


# Cleans up server socket when server closes
def handle_cleanup():
    logging.info("Cleaning up server resources...")
    with clients_lock:
        for client in clients:
            try:
                client.close()
            except Exception as e:
                logging.warning(f"Error closing client connection: {e}")
    
    try:
        server_socket.shutdown(socket.SHUT_RDWR)
        server_socket.close()
    except Exception as e:
        logging.warning(f"Error closing server socket: {e}")


# Calls function to set up server, handle client connections, and cleanup when server closes
def main():
    try:
        create_socket_bind()
    except Exception as e:
        logging.error(f"Server encountered an error: {e}")
    finally:
        handle_cleanup()


if __name__ == '__main__':
    main()