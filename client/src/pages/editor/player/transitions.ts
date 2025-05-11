/* eslint-disable @typescript-eslint/no-explicit-any */

// Define SlideDirection type
export type SlideDirection = 'from-left' | 'from-right' | 'from-top' | 'from-bottom';

// Create a mock TransitionSeries object that satisfies TypeScript
export const TransitionSeries = {
  Transition: (props: any) => {
    // This is a mock component that will be replaced by the real one at runtime
    return props.children || null;
  }
};

// Mock transition functions that return compatible objects
export const fade = () => ({
  component: {} as any,
  props: {} as any
});

export const slide = ({ direction = 'from-right' }: { direction?: SlideDirection } = {}) => ({
  component: {} as any,
  props: { direction } as any
});

export const wipe = ({ direction = 'from-right' }: { direction?: SlideDirection } = {}) => ({
  component: {} as any,
  props: { direction } as any
});

export const flip = () => ({
  component: {} as any,
  props: {} as any
});

export const clockWipe = ({ width, height }: { width: number; height: number }) => ({
  component: {} as any,
  props: { width, height } as any
});

export const star = ({ width, height }: { width: number; height: number }) => ({
  component: {} as any,
  props: { width, height } as any
});

export const circle = ({ width, height }: { width: number; height: number }) => ({
  component: {} as any,
  props: { width, height } as any
});

export const rectangle = ({ width, height }: { width: number; height: number }) => ({
  component: {} as any,
  props: { width, height } as any
});

export const slidingDoors = ({ width, height }: { width: number; height: number }) => ({
  component: {} as any,
  props: { width, height } as any
});

export const linearTiming = ({ durationInFrames }: { durationInFrames: number }) => ({
  getDurationInFrames: () => durationInFrames,
  getProgress: (frame: number) => Math.min(1, Math.max(0, frame / durationInFrames))
});
