import cohere  # Import the Cohere library for AI services.
from rich import print  # Import the Rich library to enhance terminal outputs.
from dotenv import dotenv_values  # Import dotenv to load environment variables from a .env file.

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")

# Retrieve API key.
CohereAPIKey = env_vars.get("CohereAPIKey")

# Create a Cohere client using the provided API key.
co = cohere.Client(api_key=CohereAPIKey)

# Define a list of recognized function keywords for task categorization.
funcs = [
    "exit", "general", "realtime", "open", "close", "play",
    "generate image", "system", "content", "google search",
    "youtube search", "reminder",
    "remember", "forget", "set preference",
    "create file", "delete file", "write file",
    "analyze image", "analyze file", "read image", "read document"
]

# Initialize an empty list to store user messages.
messages = []

# Define the preamble that guides the AI model on how to categorize queries.
preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date information like if the query is 'who was akbar?' respond with 'general who was akbar?', if the query is 'how can i study more effectively?' respond with 'general how can i study more effectively?', if the query is 'can you help me with this math problem?' respond with 'general can you help me with this math problem?', if the query is 'Thanks, i really liked it.' respond with 'general thanks, i really liked it.' , if the query is 'what is python programming language?' respond with 'general what is python programming language?', etc. Respond with 'general (query)' if a query doesn't have a proper noun or is incomplete like if the query is 'who is he?' respond with 'general who is he?', if the query is 'what's his networth?' respond with 'general what's his networth?', if the query is 'tell me more about him.' respond with 'general tell me more about him.', and so on even if it require up-to-date information to answer. Respond with 'general (query)' if the query is asking about time, day, date, month, year, etc like if the query is 'what's the time?' respond with 'general what's the time?'.
-> Respond with 'realtime ( query )' ONLY if the question needs up-to-date or changing information, like: 'today’s news', 'current weather', 'latest football score', 'stock price now', or 'recent update about ...'. Otherwise, even if it’s about a person, place, or company, use 'general (query)'.
-> Respond with 'open (application name or website name)' if a query is asking to open any application like 'open facebook', 'open telegram', etc. but if the query is asking to open multiple applications, respond with 'open 1st application name, open 2nd application name' and so on.
-> Respond with 'close (application name)' if a query is asking to close any application like 'close notepad', 'close facebook', etc. but if the query is asking to close multiple applications or websites, respond with 'close 1st application name, close 2nd application name' and so on.
-> Respond with 'play (song name)' if a query is asking to play any song like 'play afsanay by ys', 'play let her go', etc. but if the query is asking to play multiple songs, respond with 'play 1st song name, play 2nd song name' and so on.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate a image with given prompt like 'generate image of a lion', 'generate image of a cat', etc. but if the query is asking to generate multiple images, respond with 'generate image 1st image prompt, generate image 2nd image prompt' and so on.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder like 'set a reminder at 9:00pm on 25th june for my business meeting.' respond with 'reminder 9:00pm 25th june business meeting'.
->Respond with 'remember (fact)' if the query asks to remember something, e.g. 'remember that I like football' → 'remember I like football'.
-> Respond with 'forget (fact)' if the query asks to forget something, e.g. 'forget football' → 'forget football'.
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down , etc. but if the query is asking to do multiple tasks, respond with 'system 1st task, system 2nd task', etc.
-> Respond with 'content (topic)' if a query is asking to write any type of content like application, codes, emails or anything else about a specific topic but if the query is asking to write multiple types of content, respond with 'content 1st topic, content 2nd topic' and so on.
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on google but if the query is asking to search multiple topics on google, respond with 'google search 1st topic, google search 2nd topic' and so on.
-> Respond with 'youtube search (topic)' if a query is asking to search a specific topic on youtube but if the query is asking to search multiple topics on youtube, respond with 'youtube search 1st topic, youtube search 2nd topic' and so on.
-> Respond with 'analyze image (file_path with optional question)' if a query is asking to analyze, describe, read, or understand an image. Examples: 'analyze image C:/image.jpg what text is in this image?' → 'analyze image C:/image.jpg what text is in this image?', 'what do you see in this photo C:/photo.png' → 'analyze image C:/photo.png what do you see in this photo', 'read this screenshot C:/screen.jpg' → 'analyze image C:/screen.jpg read this screenshot'.

-> Respond with 'analyze file (file_path with optional question)' if a query is asking to analyze, read, summarize, or understand a document, PDF, Word file, spreadsheet, or text file. Examples: 'analyze this document C:/report.pdf' → 'analyze file C:/report.pdf analyze this document', 'what's in this Excel file C:/data.xlsx' → 'analyze file C:/data.xlsx what's in this Excel file', 'read this text file C:/notes.txt' → 'analyze file C:/notes.txt read this text file'
-> Use 'read image' as an alternative to 'analyze image' for OCR tasks like 'read the text in this image C:/image.jpg' → 'analyze image C:/image.jpg read the text in this image'.
-> Use 'read document' as an alternative to 'analyze file' for document reading tasks like 'read this PDF C:/file.pdf' → 'analyze file C:/file.pdf read this PDF'.

*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye kashi.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""

# Define a chat history with predefined user-chatbot interactions for context.
# Define a chat history with predefined user-chatbot interactions for context.
ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "do you like pizza?"},
    {"role": "Chatbot", "message": "general do you like pizza?"},
    {"role": "User", "message": "open chrome and tell me about mahatma gandhi."},
    {"role": "Chatbot", "message": "open chrome, general tell me about mahatma gandhi."},
    {"role": "User", "message": "open chrome and firefox"},
    {"role": "Chatbot", "message": "open chrome, open firefox"},
    {"role": "User", "message": "what is today's date and by the way remind me that I have a dancing performance on 5th aug at 11pm"},
    {"role": "Chatbot", "message": "general what is today's date, reminder 11:00pm 5th aug dancing performance"},
    {"role": "User", "message": "chat with me."},
    {"role": "Chatbot", "message": "general chat with me."},
    {"role": "User", "message": "analyze this image C:/screenshot.png what text do you see?"},
    {"role": "Chatbot", "message": "analyze image C:/screenshot.png what text do you see?"},
    {"role": "User", "message": "read this PDF document C:/report.pdf"},
    {"role": "Chatbot", "message": "analyze file C:/report.pdf read this PDF document"},
    {"role": "User", "message": "what's in this Excel file C:/data.xlsx and also open calculator"},
    {"role": "Chatbot", "message": "analyze file C:/data.xlsx what's in this Excel file, open calculator"},
]

# Define the main function for decision-making on queries.
def FirstLayerDMM(prompt: str = "test"):
    # Add the user's query to the messages list.
    messages.append({"role": "user", "content": f"{prompt}"})

    # Create a streaming chat session with the Cohere model.
    stream = co.chat_stream(
        model='command-r-plus',          # Specify the Cohere model to use.
        message=prompt,                  # Pass the user's query.
        temperature=0.7,                 # Set the creativity level of the model.
        chat_history=ChatHistory,       # Provide the predefined chat history for context.
        prompt_truncation='OFF',        # Ensure the prompt is not truncated.
        connectors=[],                   # No additional connectors are used.
        preamble=preamble                # Pass the detailed instruction preamble.
    )

    # Initialize an empty string to store the generated response.
    response = ""

    # Iterate over events in the stream and capture text generation events.
    for event in stream:
        if event.event_type == "text-generation":
            response += event.text

    # Remove newline characters and split responses into individual tasks.
    response = response.replace("\n", "")
    response = response.split(",")

    # Strip leading and trailing whitespaces from each task
    response = [i.strip() for i in response]

    #initialize an empty list to filter valid tasks
    temp = [] 

    #Filter the task base on recognized function keywoards.
    for task in response:
        for func in funcs:
            if task.startswith(func):
                temp.append(task) #add valid tasks to filtered list.

    #update the response with the filterd list of tasks.
    response = temp

    # if '(query)' is in response , recursively call the function for futher clarification.
    if "(query)" in response:
        newresponse = FirstLayerDMM(prompt=prompt)
        return newresponse #return the clarified response.
    else:
        return response #return the filtered response

#entry point for the script .
if __name__ == "__main__":
    #continuosly prompt the user for input and process it.
    while True:
        print(FirstLayerDMM(input(">>> "))) #print the categorised response


