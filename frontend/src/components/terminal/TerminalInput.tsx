import { useState, useRef, useEffect, useCallback } from 'react';
import TerminalPrompt from './TerminalPrompt';
import TerminalCursor from './TerminalCursor';

interface TerminalInputProps {
  quote: string;
  onMessageSend: (message: string) => void;
  disabled?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

const TerminalInput: React.FC<TerminalInputProps> = ({
  quote,
  onMessageSend,
  disabled = false,
  className = '',
  style = {},
}) => {
  const [inputValue, setInputValue] = useState('');
  const [showQuote, setShowQuote] = useState(true);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleContainerClick = useCallback(() => {
    // Allow clicking even when disabled (for debounce state)
    if (showQuote) {
      setShowQuote(false);
    }

    // Focus the hidden input
    inputRef.current?.focus();
    setIsFocused(true);
  }, [showQuote]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(e.target.value);
    },
    []
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !disabled && inputValue.trim()) {
        const message = inputValue.trim();
        const wordCount = message.split(/\s+/).filter(word => word.length > 0).length;
        
        if (wordCount > 200) {
          alert('Message too long! Please keep your message under 200 words.');
          return;
        }
        
        onMessageSend(message);
        setInputValue('');
      }
    },
    [disabled, inputValue, onMessageSend]
  );

  const handleInputBlur = useCallback(() => {
    setIsFocused(false);
    // If input is empty and not focused, show quote again
    if (!inputValue.trim()) {
      setShowQuote(true);
    }
  }, [inputValue]);

  // Don't auto-reset on disabled - let user stay in terminal for next message

  const isTyping = !showQuote && isFocused;

  return (
    <div
      ref={containerRef}
      className={`terminal-input-container ${className} ${
        disabled ? 'disabled' : ''
      }`}
      onClick={handleContainerClick}
      style={{
        position: 'relative', // Allow absolute positioning of children
        minHeight: '3.5rem', // Fixed height for ~2 lines + padding
        alignItems: 'flex-start', // Align content to top instead of center
        ...style, // Apply passed-in styles (visibility, opacity, etc.)
      }}
    >
      <div className="terminal-content-wrapper">
        <TerminalPrompt />

        {/* Show quote when not typing with cursor at start */}
        {showQuote && (
          <div className="terminal-text-content">
            <TerminalCursor isVisible={true} isBlinking={true} />
            <span className="quote-text" style={{ marginLeft: '0.1rem' }}>{quote}</span>
          </div>
        )}

        {/* Show user input with cursor inline - positioned after prompt */}
        {!showQuote && (
          <div className="terminal-text-content terminal-input-line">
            <span className="terminal-input-text" style={{ whiteSpace: 'pre' }}>
              {inputValue}
            </span>
            <TerminalCursor isVisible={true} isBlinking={!isTyping} />
          </div>
        )}
      </div>

      {/* Hidden input for capturing keystrokes */}
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onBlur={handleInputBlur}
        disabled={false}
        className="terminal-hidden-input"
        autoComplete="off"
        spellCheck="false"
      />
    </div>
  );
};

export default TerminalInput;
