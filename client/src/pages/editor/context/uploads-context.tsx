import React, { createContext, useContext } from 'react';
import { useUploads } from '../hooks/use-uploads';
import { IImage, IVideo, IAudio } from '@designcombo/types';

type UploadedFile = Partial<IImage | IVideo | IAudio>;

interface UploadsContextType {
  uploadedFiles: UploadedFile[];
  addUploadedFiles: (files: UploadedFile[]) => void;
  clearUploadedFiles: () => void;
  getUploadedFilesByType: (type: 'image' | 'video' | 'audio') => UploadedFile[];
}

const UploadsContext = createContext<UploadsContextType | undefined>(undefined);

export function UploadsProvider({ children }: { children: React.ReactNode }) {
  const uploadsData = useUploads();
  
  return (
    <UploadsContext.Provider value={uploadsData}>
      {children}
    </UploadsContext.Provider>
  );
}

export function useUploadsContext() {
  const context = useContext(UploadsContext);
  if (context === undefined) {
    throw new Error('useUploadsContext must be used within a UploadsProvider');
  }
  return context;
}
