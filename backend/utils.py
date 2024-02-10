import os
import json
import logging
import requests
import dataclasses

# Check for a DEBUG environment variable to set the logging level.
DEBUG = os.environ.get("DEBUG", "false")
if DEBUG.lower() == "true":
    logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG if environment variable is true.

# Retrieve the Azure Search column name for filtering based on user's groups.
AZURE_SEARCH_PERMITTED_GROUPS_COLUMN = os.environ.get("AZURE_SEARCH_PERMITTED_GROUPS_COLUMN")

class JSONEncoder(json.JSONEncoder):
    # Custom JSON encoder for encoding dataclasses to JSON.
    def default(self, o):
        # Convert dataclass objects to their dictionary representation.
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        # Fallback to the default encoder for other types.
        return super().default(o)

async def format_as_ndjson(r):
    # Asynchronously format data as Newline Delimited JSON (NDJSON).
    try:
        async for event in r:
            # Serialize each event to JSON and append a newline.
            yield json.dumps(event, cls=JSONEncoder) + "\n"
    except Exception as error:
        # Log exceptions during serialization.
        logging.exception("Exception while generating response stream: %s", error)
        # Yield an error message in JSON format.
        yield json.dumps({"error": str(error)})

def parse_multi_columns(columns: str) -> list:
    # Split a string of columns separated by "|" or "," into a list.
    if "|" in columns:
        return columns.split("|")
    else:
        return columns.split(",")

def fetchUserGroups(userToken, nextLink=None):
    # Fetch user's group memberships from Microsoft Graph API, supporting pagination.
    if nextLink:
        endpoint = nextLink  # Use the nextLink URL if provided for pagination.
    else:
        endpoint = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf?$select=id"
    
    headers = {
        'Authorization': "bearer " + userToken  # Use the provided user token for authentication.
    }
    try:
        r = requests.get(endpoint, headers=headers)
        if r.status_code != 200:
            # Log an error if the request failed.
            logging.error(f"Error fetching user groups: {r.status_code} {r.text}")
            return []
        
        r = r.json()
        if "@odata.nextLink" in r:
            # Recursively fetch additional pages of groups if a nextLink is present.
            nextLinkData = fetchUserGroups(userToken, r["@odata.nextLink"])
            r['value'].extend(nextLinkData)
        
        return r['value']  # Return the list of user groups.
    except Exception as e:
        # Log any exceptions that occur.
        logging.error(f"Exception in fetchUserGroups: {e}")
        return []

def generateFilterString(userToken):
    # Generate a filter string for Azure Search queries based on user group membership.
    userGroups = fetchUserGroups(userToken)  # Fetch user's groups.

    if not userGroups:
        logging.debug("No user groups found")

    # Create a filter string using the group IDs.
    group_ids = ", ".join([obj['id'] for obj in userGroups])
    return f"{AZURE_SEARCH_PERMITTED_GROUPS_COLUMN}/any(g:search.in(g, '{group_ids}'))"

def format_non_streaming_response(chatCompletion, history_metadata, message_uuid=None):
    # Format a response for non-streaming content.
    response_obj = {
        "id": message_uuid if message_uuid else chatCompletion.id,
        "model": chatCompletion.model,
        "created": chatCompletion.created,
        "object": chatCompletion.object,
        "choices": [{"messages": []}],
        "history_metadata": history_metadata
    }

    if len(chatCompletion.choices) > 0:
        message = chatCompletion.choices[0].message
        if message:
            if hasattr(message, "context") and message.context.get("messages"):
                for m in message.context["messages"]:
                    if m["role"] == "tool":
                        response_obj["choices"][0]["messages"].append({
                            "role": "tool",
                            "content": m["content"]
                        })
            elif hasattr(message, "context"):
                response_obj["choices"][0]["messages"].append({
                    "role": "tool",
                    "content": json.dumps(message.context),
                })
            response_obj["choices"][0]["messages"].append({
                "role": "assistant",
                "content": message.content,
            })
            return response_obj  # Return the formatted response.
    
    return {}  # Return an empty object if no content is available.

def format_stream_response(chatCompletionChunk, history_metadata, message_uuid=None):
    # Format a response for streaming content.
    response_obj = {
        "id": message_uuid if message_uuid else chatCompletionChunk.id,
        "model": chatCompletionChunk.model,
        "created": chatCompletionChunk.created,
        "object": chatCompletionChunk.object,
        "choices": [{"messages": []}],
        "history_metadata": history_metadata
    }

    if len(chatCompletionChunk.choices) > 0:
        delta = chatCompletionChunk.choices[0].delta
        if delta:
            if hasattr(delta, "context") and delta.context.get("messages"):
                for m in delta.context["messages"]:
                    if m["role"] == "tool":
                        messageObj = {
                            "role": "tool",
                            "content": m["content"]
                        }
                        response_obj["choices"][0]["messages"].append(messageObj)
                        return response_obj  # Return the response for this chunk of streaming content.
            if delta.role == "assistant" and hasattr(delta, "context"):
                messageObj = {
                    "role": "assistant",
                    "context": delta.context,
                }
                response_obj["choices"][0]["messages"].append(messageObj)
                return response_obj
            else:
                if delta.content:
                    messageObj = {
                        "role": "assistant",
                        "content": delta.content,
                    }
                    response_obj["choices"][0]["messages"].append(messageObj)
                    return response_obj
    
    return {}  # Return an empty object if no content is available.
