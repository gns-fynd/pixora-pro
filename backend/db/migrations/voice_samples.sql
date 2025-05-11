-- Voice samples table for storing voice sample metadata
CREATE TABLE IF NOT EXISTS voice_samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    gender TEXT,   -- 'male', 'female', 'neutral', etc.
    tone TEXT,     -- 'professional', 'casual', 'cheerful', etc.
    sample_url TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    is_public BOOLEAN DEFAULT false,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_voice_samples_user_id ON voice_samples(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_samples_is_public ON voice_samples(is_public);
CREATE INDEX IF NOT EXISTS idx_voice_samples_is_default ON voice_samples(is_default);
CREATE INDEX IF NOT EXISTS idx_voice_samples_gender ON voice_samples(gender);
CREATE INDEX IF NOT EXISTS idx_voice_samples_tone ON voice_samples(tone);

-- Update timestamps trigger
CREATE TRIGGER update_voice_samples_updated_at
BEFORE UPDATE ON voice_samples
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE voice_samples ENABLE ROW LEVEL SECURITY;

-- Voice samples policies - users can see their own samples and public samples
CREATE POLICY voice_samples_select ON voice_samples
    FOR SELECT
    USING (is_public OR auth.uid() = user_id);

-- Only admins and owners can insert, update, delete
CREATE POLICY voice_samples_insert_own ON voice_samples
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY voice_samples_update_own ON voice_samples
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY voice_samples_delete_own ON voice_samples
    FOR DELETE
    USING (auth.uid() = user_id);

-- Create a bucket for voice samples if it doesn't exist
INSERT INTO storage.buckets (id, name, public)
VALUES ('voice-samples', 'Voice sample audio files', true)
ON CONFLICT (id) DO NOTHING;

-- Voice samples bucket policies
CREATE POLICY voice_samples_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'voice-samples');

CREATE POLICY voice_samples_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'voice-samples' AND
        auth.uid() IS NOT NULL
    );

-- Add some default voice samples
INSERT INTO voice_samples (name, description, gender, tone, sample_url, is_default, is_public)
VALUES 
    ('Default Male', 'Professional male voice for narration', 'male', 'professional', 'https://pixora-public.storage.googleapis.com/voice-samples/default-male.wav', true, true),
    ('Default Female', 'Professional female voice for narration', 'female', 'professional', 'https://pixora-public.storage.googleapis.com/voice-samples/default-female.wav', true, true),
    ('Casual Male', 'Casual conversational male voice', 'male', 'casual', 'https://pixora-public.storage.googleapis.com/voice-samples/casual-male.wav', false, true),
    ('Casual Female', 'Casual conversational female voice', 'female', 'casual', 'https://pixora-public.storage.googleapis.com/voice-samples/casual-female.wav', false, true)
ON CONFLICT (id) DO NOTHING;

-- Update settings if needed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'settings'
        AND column_name = 'default_voice_sample_url'
    ) THEN
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            value TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
        
        -- Add default voice sample URL setting
        INSERT INTO settings (key, value)
        VALUES ('default_voice_sample_url', 'https://pixora-public.storage.googleapis.com/voice-samples/default-male.wav')
        ON CONFLICT (key) DO NOTHING;
    ELSE
        -- Update default voice sample URL if settings table exists
        INSERT INTO settings (key, value)
        VALUES ('default_voice_sample_url', 'https://pixora-public.storage.googleapis.com/voice-samples/default-male.wav')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
    END IF;
END
$$;