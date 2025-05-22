# Conversation Storage System

This directory contains SQL scripts for setting up the conversation storage system in Supabase.

## Overview

The conversation storage system consists of two main tables:

1. `conversations` - Stores metadata about conversations
2. `conversation_messages` - Stores individual messages within conversations

## Tables

### conversations

Stores metadata about conversations between users and the AI assistant.

| Column      | Type      | Description                                   |
|-------------|-----------|-----------------------------------------------|
| id          | UUID      | Primary key                                   |
| user_id     | UUID      | Foreign key to auth.users                     |
| video_id    | UUID      | Optional foreign key to videos                |
| metadata    | JSONB     | Additional metadata about the conversation    |
| created_at  | TIMESTAMP | When the conversation was created             |
| updated_at  | TIMESTAMP | When the conversation was last updated        |

### conversation_messages

Stores individual messages within conversations.

| Column          | Type      | Description                                   |
|-----------------|-----------|-----------------------------------------------|
| id              | UUID      | Primary key                                   |
| conversation_id | UUID      | Foreign key to conversations                  |
| role            | TEXT      | Role of the message sender (system, user, assistant, function) |
| content         | TEXT      | Content of the message                        |
| name            | TEXT      | Optional name for function messages           |
| function_call   | JSONB     | Optional function call data for assistant messages |
| sequence_order  | INTEGER   | Order of the message in the conversation      |
| created_at      | TIMESTAMP | When the message was created                  |

## Setup

To set up the conversation storage system, run the `create_conversation_tables.sql` script in the Supabase SQL editor.

## Row Level Security

The tables have Row Level Security (RLS) enabled to ensure that users can only access their own conversations and messages.

## Indexes

The following indexes are created for better query performance:

- `idx_conversations_user_id` - Index on user_id in conversations
- `idx_conversations_video_id` - Index on video_id in conversations
- `idx_conversation_messages_conversation_id` - Index on conversation_id in conversation_messages
- `idx_conversation_messages_sequence_order` - Index on sequence_order in conversation_messages

## Usage

The conversation storage system is used by the ChatAgent to store and retrieve conversation history. This allows the AI assistant to maintain context across multiple sessions and provide more coherent responses.

When a user starts a new conversation, a new entry is created in the `conversations` table. As the user and AI assistant exchange messages, they are stored in the `conversation_messages` table with the appropriate `conversation_id`.

The `metadata` field in the `conversations` table can be used to store additional information about the conversation, such as the current state of the video generation process, references to generated assets, or any other context that needs to be maintained across sessions.
