import socket
import threading
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Global list for clients and a lock for thread safety
clients = []
clients_lock = threading.Lock()

def handle_client(client_socket, address):
    try:
        # Receive the client's name
        client_name = client_socket.recv(1024).decode().strip()
        logging.info(f"{client_name} has joined the chat from {address}")

        while True:
            data = client_socket.recv(1024)

            if not data:
                logging.info(f"{client_name} disconnected.")
                break

            try:
                # Decode the JSON message
                message = json.loads(data.decode())
                timestamp = datetime.now().strftime("%H:%M:%S")
                broadcast_data = {
                    "timestamp": timestamp,
                    "name": client_name,
                    "text": message.get("text", "")
                }

                logging.debug(f"{timestamp} - {client_name}: {message['text']}")

                # Broadcast the message
                broadcast(broadcast_data, client_socket)

            except json.JSONDecodeError as e:
                logging.warning(f"Invalid JSON received from {client_name}: {data.decode()} - {e}")
                continue

    except (ConnectionResetError, ConnectionAbortedError) as e:
        logging.warning(f"Connection lost with {client_name}: {e}")

    finally:
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()

def broadcast(message, sender_socket):
    with clients_lock:
        for client in clients:
            if client != sender_socket:
                try:
                    client.send(json.dumps(message).encode())
                except Exception as e:
                    logging.warning(f"Error sending message to client: {e}")
                    clients.remove(client)

def create_socket_bind(host='0.0.0.0', port=8888):
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    logging.info(f"Server is listening on {host}:{port}")

def handle_cleanup():
    with clients_lock:
        for client in clients:
            try:
                client.close()
            except Exception as e:
                logging.warning(f"Error closing client connection: {e}")
    server_socket.shutdown(socket.SHUT_RDWR)
    server_socket.close()

def main():
    try:
        create_socket_bind()

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                with clients_lock:
                    clients.append(client_socket)

                # Start a new thread for each client
                client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
                client_thread.start()

            except OSError as e:
                logging.error(f"Server socket error: {e}")
                break  # Exit loop if the server is closed

    except KeyboardInterrupt:
        logging.info("\nShutting down server...")

    finally:
        handle_cleanup()

if __name__ == '__main__':
    main()