# Voice2Notion

A voice-to-Notion application that allows you to create Notion pages using voice input. The project consists of an iOS app for recording audio and a Python server that processes the audio and creates Notion pages using LangChain and OpenAI.

## Project Structure

```
.
├── Voice2NotionApp/       # iOS SwiftUI application
└── Voice2NotionServer/    # Python FastAPI server
```

## Setup

### iOS App Setup
1. Open the `Voice2NotionApp` directory in Xcode
2. Build and run the project
3. Grant microphone permissions when prompted

### Server Setup
1. Navigate to the `Voice2NotionServer` directory
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   NOTION_TOKEN=your_notion_integration_token
   NOTION_PAGE_ID=your_notion_page_id
   NOTION_MOVIE_DATABASE_ID=your_movie_database_id
   ```
5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

## Usage

1. Open the iOS app
2. Tap the microphone button to start recording
3. Speak your content
4. Tap the stop button to finish recording
5. The audio will be sent to the server, processed, and a new Notion page will be created

## Features

- Voice recording with SwiftUI
- Audio processing with OpenAI Whisper (to be implemented)
- LangChain agent for intelligent Notion page creation
- FastAPI server with CORS support
- Notion API integration

## Requirements

- iOS 15.0+
- Python 3.8+
- OpenAI API key
- Notion Integration Token 