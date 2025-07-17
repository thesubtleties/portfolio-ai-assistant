import { useRef, useState, useEffect } from 'react';
import TerminalInput from './TerminalInput';
import TerminalShimmer from './TerminalShimmer';
import CrumblingText from '../animations/CrumblingText';
import ResponseEmergence from '../animations/ResponseEmergence';
import ChatManager from '../chat/ChatManager';
import { MINIMUM_API_INTERVAL_MS } from '../../constants/animations';

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
  const terminalInputRef = useRef<HTMLDivElement>(null);
  const pendingResponseRef = useRef<string>('');
  const isDissolutionCompleteRef = useRef<boolean>(true);

  const [interactionState, setInteractionState] =
    useState<InteractionState>('idle');
  const [isFirstInteraction, setIsFirstInteraction] = useState(true);
  const [shouldCrumbleDefinition, setShouldCrumbleDefinition] = useState(false);
  const [hasDefinitionCrumbled, setHasDefinitionCrumbled] = useState(false);
  const [shouldDissolveResponse, setShouldDissolveResponse] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<string>('');
  const [pendingResponse, setPendingResponse] = useState<string>('');
  const [quote, setQuote] = useState('');
  const [isQuoteLoaded, setIsQuoteLoaded] = useState(false);
  const [shouldShowShimmer, setShouldShowShimmer] = useState(false); // Don't start immediately
  const [hasBootedUp, setHasBootedUp] = useState(false); // Track if boot animation completed
  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hasStartedBootRef = useRef(false); // Prevent multiple boot animations

  // Boot animation - trigger shimmer when quote loads
  useEffect(() => {
    if (isQuoteLoaded && !hasStartedBootRef.current) {
      console.log('🚀 Starting boot animation');
      hasStartedBootRef.current = true;
      setShouldShowShimmer(true);
    }
  }, [isQuoteLoaded]);

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
        console.log('🧪 Setting shouldDissolveResponse to true');
        isDissolutionCompleteRef.current = false; // Mark dissolution as in progress
        setShouldDissolveResponse(true);
        setInteractionState('dissolving');
      }, 50); // Small delay to let API request start first
    }
  };

  const sendMessageToServer = async (message: string) => {
    setInteractionState('sending');

    try {
      // Track start time for minimum timing guarantee
      const startTime = Date.now();

      // Use the global sendMessage function provided by ChatManager
      await (window as any).chatManager?.sendMessage(message);

      // Wait for response to arrive AND ensure minimum timing
      console.log('⏳ Waiting for response to arrive...');
      
      // Poll for pending response with a timeout
      const waitForResponse = async () => {
        const maxWaitTime = 10000; // 10 second timeout
        const pollInterval = 100; // Check every 100ms
        let totalWaited = 0;
        
        while (!pendingResponseRef.current && totalWaited < maxWaitTime) {
          await new Promise((resolve) => setTimeout(resolve, pollInterval));
          totalWaited += pollInterval;
        }
        
        if (!pendingResponseRef.current) {
          throw new Error('Response timeout - no response received within 10 seconds');
        }
      };
      
      await waitForResponse();
      console.log('📥 Response received, now ensuring minimum timing...');
      
      // Now ensure minimum animation time has passed
      const elapsed = Date.now() - startTime;
      const remainingTime = Math.max(0, MINIMUM_API_INTERVAL_MS - elapsed);

      if (remainingTime > 0) {
        console.log(
          `⏱️ Response received quickly (${elapsed}ms), waiting additional ${remainingTime}ms for smooth animation`
        );
        await new Promise((resolve) => setTimeout(resolve, remainingTime));
      }

      // Now wait for dissolution to complete before processing response
      console.log('✅ Timing complete, now waiting for dissolution to finish...');
      
      // Wait for dissolution to complete
      const waitForDissolution = async () => {
        const maxWaitTime = 5000; // 5 second timeout
        const pollInterval = 100; // Check every 100ms
        let totalWaited = 0;
        
        while (!isDissolutionCompleteRef.current && totalWaited < maxWaitTime) {
          await new Promise((resolve) => setTimeout(resolve, pollInterval));
          totalWaited += pollInterval;
        }
        
        if (!isDissolutionCompleteRef.current) {
          console.warn('⚠️ Dissolution timeout - proceeding anyway');
        }
      };
      
      await waitForDissolution();
      console.log('✅ Dissolution complete, now processing response');
      
      setCurrentResponse(pendingResponseRef.current);
      setPendingResponse(''); // Clear pending state
      pendingResponseRef.current = ''; // Clear pending ref
      console.log('🧪 Setting shouldDissolveResponse to false before new response');
      setShouldDissolveResponse(false);
      setInteractionState('responding');
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
    // Store response as pending instead of setting it immediately
    console.log('📦 Response received, storing as pending until timing completes:', {
      length: chunk.length,
      preview: chunk.substring(0, 50)
    });
    setPendingResponse(chunk);
    pendingResponseRef.current = chunk; // Also store in ref for immediate access
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
                isDissolutionCompleteRef.current = true; // Mark dissolution as complete
                setCurrentResponse(''); // Clear only after dissolve animation
                setShouldDissolveResponse(false);
              }}
            />
          </div>
        )}
      </div>

      {/* Terminal Input Section - always rendered but invisible until quote loads */}
      <div ref={terminalInputRef} className="terminal-input-wrapper" style={{ position: 'relative' }}>
        <TerminalInput
          quote={quote}
          onMessageSend={handleMessageSend}
          disabled={
            interactionState === 'sending' || interactionState === 'receiving'
          }
          className="terminal-input-section"
          style={{
            visibility: hasBootedUp ? 'visible' : 'hidden',
            opacity: hasBootedUp ? 1 : 0,
            transition: 'opacity 0.5s ease-in',
          }}
        />
        
        {/* Shimmer effect for idle state - positioned relative to input */}
        <TerminalShimmer
          containerRef={terminalInputRef}
          triggerAnimation={shouldShowShimmer}
          onComplete={() => {
            console.log('✅ Boot animation complete');
            setHasBootedUp(true);
          }}
        />
      </div>

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
