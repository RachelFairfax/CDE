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
    print(f"Accepted connection from {address}")
    #Get client name
    timestamp = datetime.now().strftime('%H:%M:%S')#Format timestamp to Hour:Minute:Second
    client_name = client_socket.recv(1024).decode()
    broadcastData = {'timestamp': timestamp, 'name': 'SERVER', 'text': client_name + ' has joined the chat'}
    broadcast(broadcastData, server_socket)
    print(f"{client_name} has joined the chat")

    #Create message handle loop
    while True:
        data = client_socket.recv(1024) #Assign JSON data to variable
        #If no data received - client disconnected
        if not data:
            print(f"{client_name} disconnected")
            break

        #Decode JSON message
        message = json.loads(data.decode())#Load messages from clients from JSON data
        timestamp = datetime.now().strftime('%H:%M:%S')#Format datetime to be Hour:Minute:Second
        message['timestamp'] = timestamp
        message['name'] = client_name
        print(message)

        #Debugging to display received message with timestamp and sender name
        print(f"(Debugging) {timestamp} - {client_name}: {message['text']}")

        #Broadcast message to all connected clients
        broadcast(message, client_socket)

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
        