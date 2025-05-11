# Loader Component

A versatile animated loader component with progress indication and customizable animations.

## Features

- **Progress Tracking**: Display progress percentage with a visual indicator
- **Auto Animation**: Option to automatically animate the progress bar
- **Custom Duration**: Configurable animation speed
- **Informative Messages**: Display status messages below the loader
- **Animated Icons**: Engaging animation with media-related icons

## Usage

```tsx
import { Loader } from '@/components/ui/loader';

// Basic usage with static progress
<Loader progress={75} message="Loading content..." />

// Auto-animated loader (for indeterminate progress)
<Loader autoAnimate={true} message="Processing..." />

// Custom animation duration (in milliseconds)
<Loader autoAnimate={true} duration={3000} message="Faster animation" />
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `progress` | `number` | `0` | The progress percentage (0-100) |
| `autoAnimate` | `boolean` | `false` | Whether to animate the progress automatically |
| `duration` | `number` | `6000` | The duration of the animation in milliseconds (only used when autoAnimate is true) |
| `message` | `string` | `undefined` | Optional message to display below the loader |
| `className` | `string` | `''` | Optional className for additional styling |

## Examples

### Static Progress

```tsx
<Loader progress={25} message="25% Complete" />
```

### Auto-Animated (Indeterminate)

```tsx
<Loader autoAnimate={true} message="Processing..." />
```

### Complete State

```tsx
<Loader progress={100} message="Task completed!" />
```

### Custom Animation Speed

```tsx
<Loader autoAnimate={true} duration={3000} message="Faster animation (3s)" />
```

## Demo

Visit `/loader-demo` to see the Loader component in action with various configurations.

## Implementation Details

The Loader component uses CSS animations to create an engaging visual experience:

- SVG icons representing media-related actions (video, audio, music, text)
- CSS animations for icon movement and transitions
- Progress bar with smooth transitions
- Percentage counter that updates in real-time

The animations are implemented using CSS keyframes and are added to the document dynamically when the component is mounted.
