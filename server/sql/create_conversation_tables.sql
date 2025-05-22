-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create conversation_messages table for storing individual messages
CREATE TABLE IF NOT EXISTS conversation_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'function')),
  content TEXT NOT NULL,
  name TEXT, -- For function messages
  function_call JSONB, -- For assistant messages with function calls
  sequence_order INTEGER NOT NULL, -- To maintain message order
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_video_id ON conversations(video_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_sequence_order ON conversation_messages(sequence_order);

-- Enable Row Level Security
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

-- Create policies for conversations
CREATE POLICY "Users can view their own conversations" 
  ON conversations FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own conversations" 
  ON conversations FOR INSERT 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own conversations" 
  ON conversations FOR UPDATE 
  USING (auth.uid() = user_id);

-- Create policies for conversation_messages
CREATE POLICY "Users can view messages in their conversations" 
  ON conversation_messages FOR SELECT 
  USING (EXISTS (
    SELECT 1 FROM conversations 
    WHERE conversations.id = conversation_messages.conversation_id 
    AND conversations.user_id = auth.uid()
  ));

CREATE POLICY "Users can insert messages in their conversations" 
  ON conversation_messages FOR INSERT 
  WITH CHECK (EXISTS (
    SELECT 1 FROM conversations 
    WHERE conversations.id = conversation_messages.conversation_id 
    AND conversations.user_id = auth.uid()
  ));
