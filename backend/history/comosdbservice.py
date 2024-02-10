import uuid
from datetime import datetime
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions

# Class definition for interacting with Azure Cosmos DB to manage conversations and messages.
class CosmosConversationClient():
    
    # Initializes the client with the necessary configuration to connect to Cosmos DB.
    def __init__(self, cosmosdb_endpoint: str, credential: any, database_name: str, container_name: str, enable_message_feedback: bool = False):
        # Store the provided configuration details.
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.credential = credential
        self.database_name = database_name
        self.container_name = container_name
        self.enable_message_feedback = enable_message_feedback
        
        # Attempt to create a CosmosClient instance. Catch and handle errors related to HTTP responses or authentication.
        try:
            self.cosmosdb_client = CosmosClient(self.cosmosdb_endpoint, credential=credential)
        except exceptions.CosmosHttpResponseError as e:
            if e.status_code == 401:
                raise ValueError("Invalid credentials") from e
            else:
                raise ValueError("Invalid CosmosDB endpoint") from e

        # Get database and container clients, handling errors if the specified resources are not found.
        try:
            self.database_client = self.cosmosdb_client.get_database_client(database_name)
        except exceptions.CosmosResourceNotFoundError:
            raise ValueError("Invalid CosmosDB database name") 
        
        try:
            self.container_client = self.database_client.get_container_client(container_name)
        except exceptions.CosmosResourceNotFoundError:
            raise ValueError("Invalid CosmosDB container name") 
        
    # Checks the initialization status of the CosmosDB client, database, and container.
    async def ensure(self):
        # Verify that all required clients are initialized.
        if not self.cosmosdb_client or not self.database_client or not self.container_client:
            return False, "CosmosDB client not initialized correctly"
            
        # Attempt to read the database and container information, catching any errors.
        try:
            database_info = await self.database_client.read()
        except:
            return False, f"CosmosDB database {self.database_name} on account {self.cosmosdb_endpoint} not found"
        
        try:
            container_info = await self.container_client.read()
        except:
            return False, f"CosmosDB container {self.container_name} not found"
            
        return True, "CosmosDB client initialized successfully"

    # Creates a new conversation document in the Cosmos DB container.
    async def create_conversation(self, user_id, title = ''):
        # Define the structure of the conversation document.
        conversation = {
            'id': str(uuid.uuid4()),  
            'type': 'conversation',
            'createdAt': datetime.utcnow().isoformat(),  
            'updatedAt': datetime.utcnow().isoformat(),  
            'userId': user_id,
            'title': title
        }
        # Insert or update the conversation document in the container.
        resp = await self.container_client.upsert_item(conversation)  
        if resp:
            return resp
        else:
            return False

    # Inserts or updates a conversation document.
    async def upsert_conversation(self, conversation):
        # Perform the upsert operation and return the response.
        resp = await self.container_client.upsert_item(conversation)
        if resp:
            return resp
        else:
            return False

    # Deletes a conversation document based on the user ID and conversation ID.
    async def delete_conversation(self, user_id, conversation_id):
        # Attempt to read and then delete the specified conversation document.
        conversation = await self.container_client.read_item(item=conversation_id, partition_key=user_id)        
        if conversation:
            resp = await self.container_client.delete_item(item=conversation_id, partition_key=user_id)
            return resp
        else:
            return True

    # Deletes messages within a conversation.
    async def delete_messages(self, conversation_id, user_id):
        # Retrieve all messages for the specified conversation.
        messages = await self.get_messages(user_id, conversation_id)
        response_list = []
        if messages:
            # Delete each message and collect responses.
            for message in messages:
                resp = await self.container_client.delete_item(item=message['id'], partition_key=user_id)
                response_list.append(resp)
            return response_list

    # Retrieves a list of conversations for a user, with optional sorting and pagination.
    async def get_conversations(self, user_id, limit, sort_order = 'DESC', offset = 0):
        # Define query parameters and the SQL query for retrieving conversations.
        parameters = [
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c where c.userId = @userId and c.type='conversation' order by c.updatedAt {sort_order}"
        if limit is not None:
            query += f" offset {offset} limit {limit}" 
        
        # Execute the query and collect results.
        conversations = []
        async for item in self.container_client.query_items(query=query, parameters=parameters):
            conversations.append(item)
        
        return conversations

    # Retrieves a specific conversation based on the user ID and conversation ID.
    async def get_conversation(self, user_id, conversation_id):
        # Define query parameters and the SQL query for retrieving a single conversation.
        parameters = [
            {
                'name': '@conversationId',
                'value': conversation_id
            },
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c where c.id = @conversationId and c.type='conversation' and c.userId = @userId"
        conversations = []
        async for item in self.container_client.query_items(query=query, parameters=parameters):
            conversations.append(item)

        # Return the first conversation found, or None if no conversation matches.
        if len(conversations) == 0:
            return None
        else:
            return conversations[0]

    # Creates a new message within a conversation.
    async def create_message(self, uuid, conversation_id, user_id, input_message: dict):
        # Define the structure of the message document.
        message = {
            'id': uuid,
            'type': 'message',
            'userId' : user_id,
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'conversationId' : conversation_id,
            'role': input_message['role'],
            'content': input_message['content']
        }

        # Optionally add feedback field to the message document.
        if self.enable_message_feedback:
            message['feedback'] = ''
        
        # Insert or update the message document, and update the conversation's updatedAt field.
        resp = await self.container_client.upsert_item(message)  
        if resp:
            conversation = await self.get_conversation(user_id, conversation_id)
            if not conversation:
                return "Conversation not found"
            conversation['updatedAt'] = message['createdAt']
            await self.upsert_conversation(conversation)
            return resp
        else:
            return False
    
    # Updates the feedback field of a message document.
    async def update_message_feedback(self, user_id, message_id, feedback):
        # Retrieve the message document and update its feedback field.
        message = await self.container_client.read_item(item=message_id, partition_key=user_id)
        if message:
            message['feedback'] = feedback
            resp = await self.container_client.upsert_item(message)
            return resp
        else:
            return False

    # Retrieves all messages within a specific conversation.
    async def get_messages(self, user_id, conversation_id):
        # Define query parameters and the SQL query for retrieving messages.
        parameters = [
            {
                'name': '@conversationId',
                'value': conversation_id
            },
            {
                'name': '@userId',
                'value': user_id
            }
        ]
        query = f"SELECT * FROM c WHERE c.conversationId = @conversationId AND c.type='message' AND c.userId = @userId ORDER BY c.timestamp ASC"
        messages = []
        async for item in self.container_client.query_items(query=query, parameters=parameters):
            messages.append(item)

        return messages
