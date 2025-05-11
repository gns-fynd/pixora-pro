-- Pixora AI Database Schema
-- This file contains the complete database schema for the Pixora AI application
-- including tables, indexes, RLS policies, and storage buckets.

-- Enable PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- =============================================================================
-- TABLES
-- =============================================================================

-- Profiles table for user information
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    avatar_url TEXT,
    credits INTEGER NOT NULL DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Videos table for video metadata
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Untitled video',
    prompt TEXT NOT NULL,
    aspect_ratio TEXT NOT NULL DEFAULT '16:9',
    duration INTEGER NOT NULL DEFAULT 30,
    style TEXT DEFAULT 'cinematic',
    status TEXT NOT NULL DEFAULT 'draft',
    thumbnail_url TEXT,
    output_url TEXT,
    credits_used INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Scenes table for scene data
CREATE TABLE IF NOT EXISTS scenes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,
    visual_description TEXT NOT NULL,
    audio_description TEXT,
    duration INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'pending',
    image_url TEXT,
    video_url TEXT,
    audio_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Generation jobs table for tracking video generation
CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    progress FLOAT NOT NULL DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Credit transactions table for tracking credit usage
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Timeline data table for video editing
CREATE TABLE IF NOT EXISTS timeline_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    is_current BOOLEAN NOT NULL DEFAULT true,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Profiles indexes
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- Videos indexes
CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at);

-- Scenes indexes
CREATE INDEX IF NOT EXISTS idx_scenes_video_id ON scenes(video_id);
CREATE INDEX IF NOT EXISTS idx_scenes_order_index ON scenes(order_index);
CREATE INDEX IF NOT EXISTS idx_scenes_status ON scenes(status);

-- Generation jobs indexes
CREATE INDEX IF NOT EXISTS idx_generation_jobs_video_id ON generation_jobs(video_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_status ON generation_jobs(status);

-- Credit transactions indexes
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON credit_transactions(created_at);

-- Timeline data indexes
CREATE INDEX IF NOT EXISTS idx_timeline_data_video_id ON timeline_data(video_id);
CREATE INDEX IF NOT EXISTS idx_timeline_data_is_current ON timeline_data(is_current);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for profiles table
CREATE TRIGGER update_profiles_updated_at
BEFORE UPDATE ON profiles
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger for videos table
CREATE TRIGGER update_videos_updated_at
BEFORE UPDATE ON videos
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger for scenes table
CREATE TRIGGER update_scenes_updated_at
BEFORE UPDATE ON scenes
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger for generation_jobs table
CREATE TRIGGER update_generation_jobs_updated_at
BEFORE UPDATE ON generation_jobs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger for timeline_data table
CREATE TRIGGER update_timeline_data_updated_at
BEFORE UPDATE ON timeline_data
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Function to ensure only one current timeline per video
CREATE OR REPLACE FUNCTION ensure_single_current_timeline()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current THEN
        UPDATE timeline_data
        SET is_current = false
        WHERE video_id = NEW.video_id AND id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for timeline_data table to ensure only one current timeline
CREATE TRIGGER ensure_single_current_timeline_trigger
BEFORE INSERT OR UPDATE ON timeline_data
FOR EACH ROW
EXECUTE FUNCTION ensure_single_current_timeline();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_data ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY profiles_select_own ON profiles
    FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY profiles_insert_own ON profiles
    FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY profiles_update_own ON profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Videos policies
CREATE POLICY videos_select_own ON videos
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY videos_insert_own ON videos
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY videos_update_own ON videos
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY videos_delete_own ON videos
    FOR DELETE
    USING (auth.uid() = user_id);

-- Scenes policies
CREATE POLICY scenes_select_own ON scenes
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = scenes.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY scenes_insert_own ON scenes
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = scenes.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY scenes_update_own ON scenes
    FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = scenes.video_id
        AND videos.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = scenes.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY scenes_delete_own ON scenes
    FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = scenes.video_id
        AND videos.user_id = auth.uid()
    ));

-- Generation jobs policies
CREATE POLICY generation_jobs_select_own ON generation_jobs
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = generation_jobs.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY generation_jobs_insert_own ON generation_jobs
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = generation_jobs.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY generation_jobs_update_own ON generation_jobs
    FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = generation_jobs.video_id
        AND videos.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = generation_jobs.video_id
        AND videos.user_id = auth.uid()
    ));

-- Credit transactions policies
CREATE POLICY credit_transactions_select_own ON credit_transactions
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY credit_transactions_insert_own ON credit_transactions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Timeline data policies
CREATE POLICY timeline_data_select_own ON timeline_data
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = timeline_data.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY timeline_data_insert_own ON timeline_data
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = timeline_data.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY timeline_data_update_own ON timeline_data
    FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = timeline_data.video_id
        AND videos.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = timeline_data.video_id
        AND videos.user_id = auth.uid()
    ));

CREATE POLICY timeline_data_delete_own ON timeline_data
    FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM videos
        WHERE videos.id = timeline_data.video_id
        AND videos.user_id = auth.uid()
    ));

-- =============================================================================
-- STORAGE BUCKETS
-- =============================================================================

-- Create storage buckets
INSERT INTO storage.buckets (id, name, public) VALUES
    ('default', 'Default storage bucket', true),
    ('videos', 'Video files', true),
    ('images', 'Image files', true),
    ('audio', 'Audio files', true),
    ('thumbnails', 'Video thumbnails', true),
    ('scene-images', 'Scene image assets', true),
    ('scene-videos', 'Scene video assets', true),
    ('scene-audio', 'Scene audio assets', true),
    ('output-videos', 'Final rendered videos', true)
ON CONFLICT (id) DO NOTHING;

-- Storage bucket policies
-- Default bucket policy
CREATE POLICY default_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'default');

CREATE POLICY default_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'default' AND
        auth.uid() IS NOT NULL
    );

-- Videos bucket policy
CREATE POLICY videos_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'videos');

CREATE POLICY videos_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'videos' AND
        auth.uid() IS NOT NULL
    );

-- Images bucket policy
CREATE POLICY images_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'images');

CREATE POLICY images_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'images' AND
        auth.uid() IS NOT NULL
    );

-- Audio bucket policy
CREATE POLICY audio_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'audio');

CREATE POLICY audio_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'audio' AND
        auth.uid() IS NOT NULL
    );

-- Thumbnails bucket policy
CREATE POLICY thumbnails_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'thumbnails');

CREATE POLICY thumbnails_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'thumbnails' AND
        auth.uid() IS NOT NULL
    );

-- Scene images bucket policy
CREATE POLICY scene_images_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'scene-images');

CREATE POLICY scene_images_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'scene-images' AND
        auth.uid() IS NOT NULL
    );

-- Scene videos bucket policy
CREATE POLICY scene_videos_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'scene-videos');

CREATE POLICY scene_videos_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'scene-videos' AND
        auth.uid() IS NOT NULL
    );

-- Scene audio bucket policy
CREATE POLICY scene_audio_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'scene-audio');

CREATE POLICY scene_audio_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'scene-audio' AND
        auth.uid() IS NOT NULL
    );

-- Output videos bucket policy
CREATE POLICY output_videos_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'output-videos');

CREATE POLICY output_videos_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'output-videos' AND
        auth.uid() IS NOT NULL
    );

-- Add delete policies for all buckets (owner only)
CREATE POLICY storage_objects_delete_policy ON storage.objects
    FOR DELETE
    USING (auth.uid() = owner);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to handle user registration
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, username, full_name, credits)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'username',
        NEW.raw_user_meta_data->>'full_name',
        10
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for user registration
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION handle_new_user();

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Create an admin user if it doesn't exist
-- Note: In a real application, you would use a more secure method to create the admin user
INSERT INTO profiles (id, email, username, full_name, credits)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'admin@pixora.ai',
    'admin',
    'Admin User',
    1000
)
ON CONFLICT (id) DO NOTHING;
