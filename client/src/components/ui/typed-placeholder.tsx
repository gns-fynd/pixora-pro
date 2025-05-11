import { useState, useEffect, useRef } from 'react';

interface TypedPlaceholderProps {
  staticText: string;
  examples: string[];
  typingSpeed?: number;
  deletingSpeed?: number;
  delayAfterComplete?: number;
  className?: string;
  onFocus?: () => void;
}

export function TypedPlaceholder({
  staticText,
  examples,
  typingSpeed = 100,
  deletingSpeed = 50,
  delayAfterComplete = 2000,
  className = '',
  onFocus
}: TypedPlaceholderProps) {
  const [currentText, setCurrentText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(true);
  // Add ellipsis to each example
  const processedExamples = examples.map(example => `${example}...`);
  const currentExample = processedExamples[exampleIndex];
  const containerRef = useRef<HTMLDivElement>(null);

  // Prevent auto-focus on component mount
  useEffect(() => {
    // Start typing animation after a short delay
    const timer = setTimeout(() => {
      setIsTyping(true);
    }, 500);
    
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!isTyping) return;

    let timeout: NodeJS.Timeout;

    if (isDeleting) {
      // Deleting text
      if (currentText === '') {
        setIsDeleting(false);
        setExampleIndex((prev) => (prev + 1) % examples.length);
        timeout = setTimeout(() => {}, 500); // Pause before typing next example
      } else {
        timeout = setTimeout(() => {
          setCurrentText(currentText.slice(0, -1));
        }, deletingSpeed);
      }
    } else {
      // Typing text
      if (currentText === currentExample) {
        // Finished typing current example
        timeout = setTimeout(() => {
          setIsDeleting(true);
        }, delayAfterComplete);
      } else {
        // Still typing
        timeout = setTimeout(() => {
          setCurrentText(currentExample.slice(0, currentText.length + 1));
        }, typingSpeed);
      }
    }

    return () => clearTimeout(timeout);
  }, [currentText, isDeleting, exampleIndex, examples, currentExample, typingSpeed, deletingSpeed, delayAfterComplete, isTyping]);

  const handleClick = () => {
    if (onFocus) {
      onFocus();
    }
    setIsTyping(false);
  };

  return (
    <div 
      ref={containerRef}
      className={`cursor-text ${className} text-base flex items-center`}
      onClick={handleClick}
    >
      <span className="text-foreground/80">{staticText}</span>
      <span className="text-foreground/60">{currentText}</span>
      <span className="animate-blink text-foreground">|</span>
    </div>
  );
}
