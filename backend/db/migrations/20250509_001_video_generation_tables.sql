-- Migration script for video generation tables
-- Creates tables for projects, script breakdowns, scenes, clips, music prompts, character profiles, and asset generations

-- Enum for transition types
CREATE TYPE transition_type AS ENUM (
    'fade',
    'slide_left',
    'slide_right',
    'zoom_in',
    'zoom_out',
    'fade_to_black',
    'crossfade'
);

-- Enum for project status
CREATE TYPE project_status AS ENUM (
    'draft',
    'script_generated',
    'script_approved',
    'generating_assets',
    'stitching_video',
    'completed',
    'failed'
);

-- Enum for asset generation status
CREATE TYPE asset_generation_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed'
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    status project_status DEFAULT 'draft',
    video_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Script breakdowns table
CREATE TABLE IF NOT EXISTS script_breakdowns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    user_prompt TEXT NOT NULL,
    rewritten_prompt TEXT NOT NULL,
    voice_character TEXT,
    character_consistency BOOLEAN DEFAULT false,
    expected_duration FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Scenes table
CREATE TABLE IF NOT EXISTS scenes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES script_breakdowns(id) ON DELETE CASCADE,
    index INTEGER NOT NULL,
    title TEXT NOT NULL,
    script TEXT NOT NULL,
    video_prompt TEXT NOT NULL,
    transition transition_type DEFAULT 'fade',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Clips table
CREATE TABLE IF NOT EXISTS clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES script_breakdowns(id) ON DELETE CASCADE,
    scene_id UUID REFERENCES scenes(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Music prompts table
CREATE TABLE IF NOT EXISTS music_prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES script_breakdowns(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Music prompt scene mappings
CREATE TABLE IF NOT EXISTS music_prompt_scenes (
    music_prompt_id UUID REFERENCES music_prompts(id) ON DELETE CASCADE,
    scene_index INTEGER NOT NULL,
    script_id UUID REFERENCES script_breakdowns(id) ON DELETE CASCADE,
    PRIMARY KEY (music_prompt_id, scene_index, script_id)
);

-- Character profiles table
CREATE TABLE IF NOT EXISTS character_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES script_breakdowns(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    image_prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Character profile images
CREATE TABLE IF NOT EXISTS character_profile_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    character_profile_id UUID REFERENCES character_profiles(id) ON DELETE CASCADE,
    view_type TEXT NOT NULL, -- 'front', 'side', 'back', 'three_quarter', 'grid'
    image_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Asset generations table
CREATE TABLE IF NOT EXISTS asset_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    scene_index INTEGER,
    asset_type TEXT NOT NULL, -- 'character', 'scene', 'audio', 'music', 'video'
    status asset_generation_status DEFAULT 'pending',
    result_url TEXT,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_script_breakdowns_project_id ON script_breakdowns(project_id);
CREATE INDEX IF NOT EXISTS idx_script_breakdowns_user_id ON script_breakdowns(user_id);
CREATE INDEX IF NOT EXISTS idx_scenes_script_id ON scenes(script_id);
CREATE INDEX IF NOT EXISTS idx_scenes_index ON scenes(index);
CREATE INDEX IF NOT EXISTS idx_clips_script_id ON clips(script_id);
CREATE INDEX IF NOT EXISTS idx_clips_scene_id ON clips(scene_id);
CREATE INDEX IF NOT EXISTS idx_music_prompts_script_id ON music_prompts(script_id);
CREATE INDEX IF NOT EXISTS idx_character_profiles_script_id ON character_profiles(script_id);
CREATE INDEX IF NOT EXISTS idx_asset_generations_project_id ON asset_generations(project_id);
CREATE INDEX IF NOT EXISTS idx_asset_generations_status ON asset_generations(status);
CREATE INDEX IF NOT EXISTS idx_asset_generations_asset_type ON asset_generations(asset_type);

-- Update timestamps triggers
CREATE TRIGGER update_projects_updated_at
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_script_breakdowns_updated_at
BEFORE UPDATE ON script_breakdowns
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scenes_updated_at
BEFORE UPDATE ON scenes
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clips_updated_at
BEFORE UPDATE ON clips
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_music_prompts_updated_at
BEFORE UPDATE ON music_prompts
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_character_profiles_updated_at
BEFORE UPDATE ON character_profiles
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_character_profile_images_updated_at
BEFORE UPDATE ON character_profile_images
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_generations_updated_at
BEFORE UPDATE ON asset_generations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE script_breakdowns ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE music_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE music_prompt_scenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE character_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE character_profile_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_generations ENABLE ROW LEVEL SECURITY;

-- Projects policies
CREATE POLICY projects_select_own ON projects
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY projects_insert_own ON projects
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY projects_update_own ON projects
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY projects_delete_own ON projects
    FOR DELETE
    USING (auth.uid() = user_id);

-- Script breakdowns policies
CREATE POLICY script_breakdowns_select_own ON script_breakdowns
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY script_breakdowns_insert_own ON script_breakdowns
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY script_breakdowns_update_own ON script_breakdowns
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY script_breakdowns_delete_own ON script_breakdowns
    FOR DELETE
    USING (auth.uid() = user_id);

-- Scenes policies (based on script ownership)
CREATE POLICY scenes_select ON scenes
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM script_breakdowns
        WHERE script_breakdowns.id = scenes.script_id
        AND script_breakdowns.user_id = auth.uid()
    ));

CREATE POLICY scenes_insert ON scenes
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM script_breakdowns
        WHERE script_breakdowns.id = scenes.script_id
        AND script_breakdowns.user_id = auth.uid()
    ));

CREATE POLICY scenes_update ON scenes
    FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM script_breakdowns
        WHERE script_breakdowns.id = scenes.script_id
        AND script_breakdowns.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM script_breakdowns
        WHERE script_breakdowns.id = scenes.script_id
        AND script_breakdowns.user_id = auth.uid()
    ));

CREATE POLICY scenes_delete ON scenes
    FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM script_breakdowns
        WHERE script_breakdowns.id = scenes.script_id
        AND script_breakdowns.user_id = auth.uid()
    ));

-- Similar policies for other tables (clips, music_prompts, etc.)
-- These follow the same pattern as the scenes policies

-- Create storage buckets for assets if they don't exist
INSERT INTO storage.buckets (id, name, public)
VALUES 
    ('character-images', 'Character images for video generation', true),
    ('scene-images', 'Scene images for video generation', true),
    ('audio-files', 'Audio files for video generation', true),
    ('music-files', 'Music files for video generation', true),
    ('video-files', 'Video files for video generation', true)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for each bucket
CREATE POLICY character_images_bucket_select_policy ON storage.objects
    FOR SELECT
    USING (bucket_id = 'character-images');

CREATE POLICY character_images_bucket_insert_policy ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'character-images' AND
        auth.uid() IS NOT NULL
    );

-- Similar policies for other buckets
