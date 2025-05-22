import { Scene, Prompt, Script } from '@/pages/scene-breakdown/types';

// Ganesh Chaturthi documentary data
export const mumbaiDocumentaryData = {
  'prompt': "create a documentary on Ganesh Chaturthi festival",
  'script_path': null,
  'script': null,
  'scenes': [
    {
      'id': 'scene-1',
      'index': 1,
      'title': "Origins of Ganesh Chaturthi",
      'script': "Ganesh Chaturthi, a festival honoring the elephant-headed deity Lord Ganesha, has been celebrated for centuries across India.",
      'visual': "Ancient temple carvings of Lord Ganesha, followed by historical paintings and illustrations showing early celebrations of the festival in Maharashtra.",
      'audio': "Ganesh Chaturthi, a festival honoring the elephant-headed deity Lord Ganesha, has been celebrated for centuries across India.",
      'video_prompt': "Ancient temple carvings of Lord Ganesha, followed by historical paintings and illustrations showing early celebrations of the festival in Maharashtra.",
      'music_prompt': "Traditional Indian classical music with tabla and sitar, creating a reverent and spiritual atmosphere.",
      'speech_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene1/speech.mp3",
      'music_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene1/music.mp3",
      'mixed_audio_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene1/mixed_audio.mp3",
      'video_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene1/video.mp4",
      'final_scene_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene1/final_scene.mp4",
      'image_url': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene1/scene1.png",
      'speech_captions': [],
      'duration': 10
    },
    {
      'id': 'scene-2',
      'index': 2,
      'title': "Idol Creation",
      'script': "Skilled artisans spend months crafting beautiful Ganesha idols from clay, plaster, and eco-friendly materials, each with its unique style and character.",
      'visual': "Time-lapse of artisans creating Ganesha idols, showing the detailed process from clay molding to intricate painting and decoration.",
      'audio': "Skilled artisans spend months crafting beautiful Ganesha idols from clay, plaster, and eco-friendly materials, each with its unique style and character.",
      'video_prompt': "Time-lapse of artisans creating Ganesha idols, showing the detailed process from clay molding to intricate painting and decoration.",
      'music_prompt': "Upbeat traditional Indian folk music with rhythmic percussion, conveying craftsmanship and artistic dedication.",
      'speech_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene2/speech.mp3",
      'music_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene2/music.mp3",
      'mixed_audio_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene2/mixed_audio.mp3",
      'video_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene2/video.mp4",
      'final_scene_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene2/final_scene.mp4",
      'image_url': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene2/scene2.png",
      'speech_captions': [],
      'duration': 10
    },
    {
      'id': 'scene-3',
      'index': 3,
      'title': "Home and Pandal Preparations",
      'script': "Families clean their homes and create elaborate shrines, while communities construct magnificent pandals (temporary structures) to house larger idols for public worship.",
      'visual': "Split-screen showing families decorating home shrines with flowers, lights, and offerings, alongside volunteers building colorful community pandals with themed decorations.",
      'audio': "Families clean their homes and create elaborate shrines, while communities construct magnificent pandals (temporary structures) to house larger idols for public worship.",
      'video_prompt': "Split-screen showing families decorating home shrines with flowers, lights, and offerings, alongside volunteers building colorful community pandals with themed decorations.",
      'music_prompt': "Cheerful devotional music with harmonium and group singing, creating a sense of community preparation and anticipation.",
      'speech_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene3/speech.mp3",
      'music_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene3/music.mp3",
      'mixed_audio_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene3/mixed_audio.mp3",
      'video_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene3/video.mp4",
      'final_scene_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene3/final_scene.mp4",
      'image_url': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene3/scene3.png",
      'speech_captions': [],
      'duration': 10
    },
    {
      'id': 'scene-4',
      'index': 4,
      'title': "Rituals and Prayers",
      'script': "The festival begins with Pranapratishtha, a ritual to invoke life in the idol, followed by 16 forms of devotional offerings known as Shodashopachara.",
      'visual': "Close-up shots of priests performing rituals with incense, flowers, and offerings, families praying together, and devotees singing bhajans (devotional songs).",
      'audio': "The festival begins with Pranapratishtha, a ritual to invoke life in the idol, followed by 16 forms of devotional offerings known as Shodashopachara.",
      'video_prompt': "Close-up shots of priests performing rituals with incense, flowers, and offerings, families praying together, and devotees singing bhajans (devotional songs).",
      'music_prompt': "Serene devotional music with bells and chanting, creating a sacred and spiritual atmosphere.",
      'speech_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene4/speech.mp3",
      'music_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene4/music.mp3",
      'mixed_audio_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene4/mixed_audio.mp3",
      'video_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene4/video.mp4",
      'final_scene_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene4/final_scene.mp4",
      'image_url': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene4/scene4.png",
      'speech_captions': [],
      'duration': 10
    },
    {
      'id': 'scene-5',
      'index': 5,
      'title': "Celebrations and Cultural Programs",
      'script': "Throughout the festival, communities organize cultural performances, music concerts, and art competitions, bringing people together in joyous celebration.",
      'visual': "Montage of dance performances, musical concerts, children's art competitions, and community feasts, all centered around the Ganesh Chaturthi theme.",
      'audio': "Throughout the festival, communities organize cultural performances, music concerts, and art competitions, bringing people together in joyous celebration.",
      'video_prompt': "Montage of dance performances, musical concerts, children's art competitions, and community feasts, all centered around the Ganesh Chaturthi theme.",
      'music_prompt': "Energetic fusion of traditional and contemporary Indian music with fast-paced dhol drums and celebratory rhythms.",
      'speech_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene5/speech.mp3",
      'music_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene5/music.mp3",
      'mixed_audio_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene5/mixed_audio.mp3",
      'video_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene5/video.mp4",
      'final_scene_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene5/final_scene.mp4",
      'image_url': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene5/scene5.png",
      'speech_captions': [],
      'duration': 10
    },
    {
      'id': 'scene-6',
      'index': 6,
      'title': "Visarjan (Immersion Ceremony)",
      'script': "The festival concludes with Visarjan, where idols are carried in grand processions to be immersed in water, symbolizing Lord Ganesha's return to Mount Kailash and the cycle of creation and dissolution.",
      'visual': "Aerial shots of massive processions with dancing, music, and chants of 'Ganpati Bappa Morya', followed by emotional scenes of idol immersion in rivers, lakes, or the sea.",
      'audio': "The festival concludes with Visarjan, where idols are carried in grand processions to be immersed in water, symbolizing Lord Ganesha's return to Mount Kailash and the cycle of creation and dissolution.",
      'video_prompt': "Aerial shots of massive processions with dancing, music, and chants of 'Ganpati Bappa Morya', followed by emotional scenes of idol immersion in rivers, lakes, or the sea.",
      'music_prompt': "Powerful crescendo of traditional dhol drums, cymbals, and group chanting of 'Ganpati Bappa Morya', creating an atmosphere of emotional farewell.",
      'speech_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene6/speech.mp3",
      'music_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene6/music.mp3",
      'mixed_audio_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene6/mixed_audio.mp3",
      'video_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene6/video.mp4",
      'final_scene_path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene6/final_scene.mp4",
      'image_url': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/scene6/scene6.png",
      'speech_captions': [],
      'duration': 10
    }
  ],
  'final_video': {
    'path': "https://mthzmmlljcydgiiwekgn.supabase.co/storage/v1/object/public/pixora/ganesh_chaturthi_246ruyiu2d7d2d/final_video.mp4",
    'duration': 60
  },
  'total_duration': 60
};

// Function to convert the data to the format expected by the scene breakdown page
export function convertToSceneBreakdownFormat() {
  const scenes: Scene[] = mumbaiDocumentaryData.scenes.map(scene => ({
    id: scene.id,
    title: scene.title,
    visual: scene.visual,
    audio: scene.audio,
    duration: scene.duration,
    image_url: scene.image_url
  }));

  const script: Script = {
    id: 'script-1',
    title: 'Ganesh Chaturthi Festival',
    content: mumbaiDocumentaryData.scenes.map(scene => scene.script).join('\n\n')
  };

  return { scenes, script };
}

// Function to get the prompt data
export function getPromptData(): Prompt {
  return {
    prompt: mumbaiDocumentaryData.prompt,
    aspectRatio: '16:9',
    duration: mumbaiDocumentaryData.total_duration,
    style: 'documentary'
  };
}