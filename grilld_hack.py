import os.path
import pickle
import base64
import time
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re
import asyncio
import aiohttp
import nest_asyncio

nest_asyncio.apply()

# Asynchronous functions for making GET requests
async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main(url):
    for _ in range(3):  # This will run the enclosed block 3 times
        tasks = []
        async with aiohttp.ClientSession() as session:
            for i in range(10):
                tasks.append(fetch(session, url))

            responses = await asyncio.gather(*tasks)
            for i, response in enumerate(responses):
                print(f"Request {i+1} completed with response length: {len(response)}")

        print("Completed one round of requests.")


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
processed_ids = set()


def get_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, prompt the user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(None)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def get_initial_unread_ids(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])
    return {message['id'] for message in messages}

def print_new_emails(service):
    global processed_ids

    # Call the Gmail API to fetch inbox
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])

    if not messages:
        print('No new emails found.')
        return

    for message in messages:
        if message['id'] in processed_ids:
            continue
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        email_data = msg['payload']['headers']

        # Extract the From header for the email
        from_name = next(value['value'] for value in email_data if value['name'] == 'From')

        # Function to process the email body text
        def process_text(text):
            # Search for the "TAKE" string followed by an https link
            match = re.search(r"TAKE\s*<(https://[^>]+)>", text)
            if match:
                link = match.group(1)
                print(link)  # Only print the link
                asyncio.run(main(link))  # Run the asynchronous function with the extracted link

        # Extract the email body
        if 'parts' in msg['payload']:
            parts = msg['payload']['parts']
            for part in parts:
                data = part['body'].get('data')
                if data:
                    byte_code = base64.urlsafe_b64decode(data)
                    text = byte_code.decode('utf-8')
                    process_text(text)
        else:
            data = msg['payload']['body'].get('data')
            if data:
                byte_code = base64.urlsafe_b64decode(data)
                text = byte_code.decode('utf-8')
                process_text(text)

        processed_ids.add(message['id'])


# def hackGrilled(secretlink):
#     tasks = []
#     async with aiohttp.ClientSession() as session:
#         for i in range(20):
#             tasks.append(fetch(session, url))

#         responses = await asyncio.gather(*tasks)
#         for i, response in enumerate(responses):
#             print(f"Request {i+1} completed with response length: {len(response)}")




service = get_service()
processed_ids = get_initial_unread_ids(service)
while True:
    print_new_emails(service)
    time.sleep(.1)


