 #Import required modules and advise user to retry if fails
try:
    import socket
    import threading
    import json
    from datetime import datetime
except ImportError:
    raise ImportError("Failed to start, close and retry")

#Function to handle client connections
def handle_client(client_socket, address):
    print(f"Accepted connection from (address)")

    #Receive the client's name
    client_name = client_socket.recv(1024).decode()
    print(f"(client_name) has joined the chat.")

    #Create message handle loop
    while True:
        data = client_socket.recv(1024) #Assign JSON data to data variable

        #If no data received, the client has disconnected
        if not data:
            print (f"(client_name) disconnected")
            break

        #Decode the JSON message
        message = json.loads(data.decode()) #Load message from clients from JSON data
        timestamp = datetime.now().strftime("%H:%M:%S") #Format timestamp to hour:min:sec
        #Create dictionary variable for the data / timestamp and senders name.
        broadcastData = {"timestamp": timestamp, "name": client_name, "text": message ["text"]}

        #Debugging to display the received message with timestamp and sender's name
        print(f" (Debugging) {timestamp} - {client_name}: {message['text']}")

        #Broadcast the message to all connected clients
        broadcast(broadcastData,client_socket)

# Function to broadcast a message to all connected clients
def broadcast(message, sender_socket):
    # Loop through all connected clients
    for client in clients:
        # If client is not the sender
        if client != sender_socket:
            # Try to send the message or remove the client
            try:
                # Encode the message as JSON and send it
                client.send(json.dumps(message).encode())
            except:
                # Remove the client if it's no longer available
                clients.remove(client)

def create_socket_bind(host='0.0.0.0', port=8888):
    global server_socket
    # Create a dictionary data set of socket data using the socket library
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Create a bind connection for clients using the library functionality and set server / port
    server_socket.bind((host, port))
    server_socket.listen(5)  # Allow up to 5 connections
    print(f"Server is listening on {host}:{port}")
    global clients  # List to store connected client sockets
    clients = []

def handle_cleanup():
    server_socket.shutdown(socket.SHUT_RDWR)
    server_socket.close()

def main():
    try:
        create_socket_bind()

        # Loop the program until exit
        while True:
            client_socket, client_address = server_socket.accept()
            clients.append(client_socket)  # Add the client socket to the list of connected clients

            # Start a new thread to handle the client
            global client_thread
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()

    finally:
        handle_cleanup()

if __name__ == '__main__':
    main()
