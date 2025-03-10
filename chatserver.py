#Import required modules - advise user retry on fail
try:
    import socket
    import threading
    import json
    from datetime import datetime
except ImportError:
    raise ImportError('Failed to start, close and retry')

ALLOWED_IPS = ['127.0.0.1', '192.168.1.100']  # Add allowed client IPs

#Handles chat client connection - responsible for receiving and sending messages to and from clients. Tracks client name and broadcasts messages to all connected clients
def handle_client(client_socket, address):
    try:
        print(f"Accepted connection from {address}")
        timestamp = datetime.now().strftime('%H:%M:%S')
        client_name = client_socket.recv(1024).decode().strip()

        if not client_name or len(client_name) > 30:
            print(f"Invalid name received from {address}. Disconnecting...")
            client_socket.close()
            return

        broadcastData = {'timestamp': timestamp, 'name': 'SERVER', 'text': f"{client_name} has joined the chat"}
        broadcast(broadcastData, server_socket)

        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break

                message = json.loads(data.decode())

                # Validate message structure
                if not isinstance(message, dict) or 'text' not in message:
                    print(f"Invalid message format from {client_name}, ignoring.")
                    continue
                
                # Limit message length (avoid spam attacks)
                if len(message['text']) > 500:
                    print(f"Message too long from {client_name}, ignoring.")
                    continue

                # Remove any harmful characters (basic input sanitation)
                message['text'] = message['text'].replace("<script>", "").replace("</script>", "")

                # Append timestamp and sender name
                message['timestamp'] = datetime.now().strftime('%H:%M:%S')
                message['name'] = client_name

                print(f"(Debugging) {message['timestamp']} - {client_name}: {message['text']}")

                broadcast(message, client_socket)

            except (json.JSONDecodeError, ValueError):
                print(f"Malformed message from {client_name}, ignoring.")
                continue

    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        print(f"{client_name} disconnected")
        clients.remove(client_socket) if client_socket in clients else None
        client_socket.close()



#Broadcasts message to all connected clients except sender
def broadcast(message, sender_socket):
    #Loop through all connected clients
    for client in clients:
        #If client not sender
        if client != sender_socket:
            #Try to send message or remove client
            try:
                #Encode message as JSON and send it
                client.send(json.dumps(message).encode())
            except:
                #Remove client if no longer available
                clients.remove(client)

#Creates socket, bind to IP address and port and listen for incoming connections. Initialise empty list clients to store connected client sockets


def create_socket_bind(host='0.0.0.0', port=8888):
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    global clients
    clients = []
    print(f'Server is listening on {host}:{port}')

    while True:
        client_socket, client_address = server_socket.accept()
        client_ip = client_address[0]

        if client_ip not in ALLOWED_IPS:
            print(f"Unauthorized connection attempt from {client_ip}")
            client_socket.close()
            continue  # Ignore unauthorized connections

        clients.append(client_socket)
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

#Cleans up server socket when server closed
def handle_cleanup():
    with clients_lock:
        for client in clients:
            try:
                client.close()
            except Exception as e:
                logging.warning(f"Error closing client connection: {e}")
    server_socket.shutdown(socket.SHUT_RDWR)
    server_socket.close()

#Calls function to set up server, handle client connections and cleanup when server closed
def main():
    try:
        create_socket_bind()
        #Loop program until exit
        while True:
            client_socket, client_address = server_socket.accept()
            clients.append(client_socket)#Add client socket to list of connected clients
            #Start new thread to handle client
            global client_thread
            client_thread = threading.Thread(target = handle_client, args = (client_socket, client_address))
            client_thread.start()
    finally:
        handle_cleanup()

if __name__ == '__main__':
    main()
        