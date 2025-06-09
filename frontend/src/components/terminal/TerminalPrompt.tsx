import React, { forwardRef } from 'react';

interface TerminalPromptProps {
  className?: string;
}

const TerminalPrompt = forwardRef<HTMLSpanElement, TerminalPromptProps>(
  ({ className = '' }, ref) => {
    return (
      <span ref={ref} className={`terminal-prompt ${className}`}>
        <span className="terminal-path">~</span>
        <span className="terminal-separator"> </span>
        <span className="terminal-directory">home</span>
        <span className="terminal-separator"> </span>
        <span className="terminal-symbol">%</span>
        <span className="terminal-separator"> </span>
      </span>
    );
  }
);

TerminalPrompt.displayName = 'TerminalPrompt';

export default TerminalPrompt;
