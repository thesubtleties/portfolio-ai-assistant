import { useRef, useState } from 'react';
import TerminalInput from './TerminalInput';
import CrumblingText from '../animations/CrumblingText';
import ResponseEmergence from '../animations/ResponseEmergence';
import ChatManager from '../chat/ChatManager';

interface TerminalInterfaceProps {
  className?: string;
}

type InteractionState =
  | 'idle'
  | 'typing'
  | 'sending'
  | 'receiving'
  | 'responding'
  | 'dissolving';

const TerminalInterface: React.FC<TerminalInterfaceProps> = ({
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const responseRef = useRef<HTMLDivElement>(null);

  const [interactionState, setInteractionState] =
    useState<InteractionState>('idle');
  const [isFirstInteraction, setIsFirstInteraction] = useState(true);
  const [shouldCrumbleDefinition, setShouldCrumbleDefinition] = useState(false);
  const [hasDefinitionCrumbled, setHasDefinitionCrumbled] = useState(false);
  const [shouldDissolveResponse, setShouldDissolveResponse] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<string>('');
  const [quote, setQuote] = useState('');
  const [isQuoteLoaded, setIsQuoteLoaded] = useState(false);

  const handleMessageSend = async (message: string) => {
    console.log('Sending message, isFirstInteraction:', isFirstInteraction);

    // If first interaction, trigger the crumbling effect
    if (isFirstInteraction) {
      console.log('Triggering definition crumbling');
      setShouldCrumbleDefinition(true);
      setIsFirstInteraction(false);

      // Backup: Hide definition after animation should complete (trembling + falling = ~4.5s max)
      setTimeout(() => {
        if (!hasDefinitionCrumbled) {
          console.log('Animation backup: hiding definition');
          setHasDefinitionCrumbled(true);
        }
      }, 5000);
    }

    // Send API request immediately - don't wait for animations
    sendMessageToServer(message);

    // If there's an existing response, dissolve it a few milliseconds after sending
    if (currentResponse) {
      console.log('Starting response dissolve after sending');
      setTimeout(() => {
        setShouldDissolveResponse(true);
        setInteractionState('dissolving');
      }, 50); // Small delay to let API request start first
    }
  };

  const sendMessageToServer = async (message: string) => {
    setInteractionState('sending');

    try {
      // Use the global sendMessage function provided by ChatManager
      const success = await (window as any).sendMessage?.(message);
      if (success) {
        setInteractionState('receiving');
      } else {
        setInteractionState('idle');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setInteractionState('idle');
    }
  };

  const handleQuoteReceived = (newQuote: string) => {
    setQuote(newQuote);
    setIsQuoteLoaded(true);
  };

  const handleResponseReceived = (chunk: string) => {
    // For streaming: accumulate chunks
    setCurrentResponse(prev => {
      // If this is the first chunk, clear previous response and start fresh
      if (interactionState !== 'responding') {
        setShouldDissolveResponse(false);
        setInteractionState('responding');
        return chunk;
      }
      // Otherwise, accumulate the chunk
      return prev + chunk;
    });

    // Since we're not streaming, set to idle immediately after response is received
    setInteractionState('idle');
  };

  return (
    <div ref={containerRef} className={`terminal-interface ${className}`}>
      {/* Main Content Area - Definition OR Response */}
      <div className="main-content-area">
        {/* Definition Section - handles its own animation and crumbling */}
        {!hasDefinitionCrumbled && (
          <CrumblingText
            shouldCrumble={shouldCrumbleDefinition}
            onComplete={() => {
              console.log('Definition crumbling complete');
              setShouldCrumbleDefinition(false);
              setHasDefinitionCrumbled(true);
            }}
          />
        )}

        {/* Response Section - positioned in same area as definition */}
        {currentResponse && (
          <div ref={responseRef} className="response-content">
            <ResponseEmergence
              response={currentResponse}
              isActive={interactionState === 'responding'}
              shouldDissolve={shouldDissolveResponse}
              onDissolveComplete={() => {
                console.log('ResponseEmergence dissolve complete');
                setCurrentResponse(''); // Clear only after dissolve animation
                setShouldDissolveResponse(false);
              }}
            />
          </div>
        )}
      </div>

      {/* Terminal Input Section - always rendered but invisible until quote loads */}
      <TerminalInput
        quote={quote}
        onMessageSend={handleMessageSend}
        disabled={
          interactionState === 'sending' || interactionState === 'receiving'
        }
        className="terminal-input-section"
        style={{
          visibility: isQuoteLoaded ? 'visible' : 'hidden',
          opacity: isQuoteLoaded ? 1 : 0,
        }}
      />

      {/* Debug info - commented out for production */}
      {/* 
      {process.env.NODE_ENV === 'development' && (
        <div
          style={{
            position: 'fixed',
            top: '10px',
            left: '10px',
            background: 'black',
            color: 'white',
            padding: '5px',
            fontSize: '12px',
            zIndex: 9999,
          }}
        >
          <div>isFirstInteraction: {isFirstInteraction.toString()}</div>
          <div>interactionState: {interactionState}</div>
          <div>
            shouldCrumbleDefinition: {shouldCrumbleDefinition.toString()}
          </div>
          <div>hasDefinitionCrumbled: {hasDefinitionCrumbled.toString()}</div>
          <div>
            Definition visible:{' '}
            {(!shouldCrumbleDefinition && !hasDefinitionCrumbled).toString()}
          </div>
        </div>
      )}
      */}

      {/* Text Dissolve Animation - now handled by ResponseEmergence */}

      {/* Chat Management */}
      <ChatManager
        onQuoteReceived={handleQuoteReceived}
        onResponseReceived={handleResponseReceived}
        onStateChange={setInteractionState}
      />
    </div>
  );
};

export default TerminalInterface;
