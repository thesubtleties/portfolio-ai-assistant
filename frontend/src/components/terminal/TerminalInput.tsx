import { useState, useRef, useEffect, useCallback } from 'react';
import TerminalPrompt from './TerminalPrompt';
import TerminalCursor from './TerminalCursor';

interface TerminalInputProps {
  quote: string;
  onMessageSend: (message: string) => void;
  disabled?: boolean;
  className?: string;
}

const TerminalInput: React.FC<TerminalInputProps> = ({
  quote,
  onMessageSend,
  disabled = false,
  className = '',
}) => {
  const [inputValue, setInputValue] = useState('');
  const [showQuote, setShowQuote] = useState(true);
  const [isFocused, setIsFocused] = useState(false);
  const [containerHeight, setContainerHeight] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleContainerClick = useCallback(() => {
    if (disabled) return;

    if (showQuote) {
      // Capture the current height before hiding the quote
      if (containerRef.current) {
        setContainerHeight(containerRef.current.offsetHeight);
      }
      setShowQuote(false);
    }

    // Focus the hidden input
    inputRef.current?.focus();
    setIsFocused(true);
  }, [disabled, showQuote]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(e.target.value);
    },
    []
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !disabled && inputValue.trim()) {
        onMessageSend(inputValue.trim());
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
      // Reset container height when going back to quote
      setContainerHeight(null);
    }
  }, [inputValue]);

  // Reset to quote when disabled (after sending)
  useEffect(() => {
    if (disabled) {
      setInputValue('');
      setShowQuote(true);
      setIsFocused(false);
      // Reset container height when going back to quote
      setContainerHeight(null);
    }
  }, [disabled]);

  const isTyping = !showQuote && isFocused;

  return (
    <div
      ref={containerRef}
      className={`terminal-input-container ${className} ${
        disabled ? 'disabled' : ''
      }`}
      onClick={handleContainerClick}
      style={{
        minHeight: containerHeight ? `${containerHeight}px` : '2.5rem',
      }}
    >
      <div className="terminal-content-wrapper">
        <TerminalPrompt />

        {/* Show quote when not typing - let it wrap naturally */}
        {showQuote && (
          <span className="terminal-text-content quote-text">{quote}</span>
        )}

        {/* Show user input with cursor inline - properly positioned */}
        {!showQuote && (
          <div className="terminal-text-content terminal-input-line">
            <span className="terminal-input-text">{inputValue}</span>
            <TerminalCursor isVisible={true} isBlinking={!isTyping} />
          </div>
        )}

        {/* Show cursor after quote when focused but not typing */}
        {showQuote && isFocused && (
          <TerminalCursor isVisible={true} isBlinking={true} />
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
        disabled={disabled}
        className="terminal-hidden-input"
        autoComplete="off"
        spellCheck="false"
      />
    </div>
  );
};

export default TerminalInput;
