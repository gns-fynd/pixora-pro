import { useState, useCallback } from 'react';
import { IImage, IVideo, IAudio } from '@designcombo/types';

type UploadedFile = Partial<IImage | IVideo | IAudio>;

export function useUploads() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  const addUploadedFiles = useCallback((files: UploadedFile[]) => {
    setUploadedFiles(prev => [...prev, ...files]);
  }, []);

  const clearUploadedFiles = useCallback(() => {
    setUploadedFiles([]);
  }, []);

  const getUploadedFilesByType = useCallback((type: 'image' | 'video' | 'audio') => {
    return uploadedFiles.filter(file => file.type === type);
  }, [uploadedFiles]);

  return {
    uploadedFiles,
    addUploadedFiles,
    clearUploadedFiles,
    getUploadedFilesByType
  };
}
