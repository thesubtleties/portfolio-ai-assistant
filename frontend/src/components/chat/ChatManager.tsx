import { useEffect, useRef, useState } from 'react';
import MessageDebouncer from './MessageDebouncer';

interface ChatManagerProps {
  onQuoteReceived: (quote: string) => void;
  onResponseReceived: (response: string) => void;
  onStateChange: (
    state: 'idle' | 'sending' | 'receiving' | 'responding'
  ) => void;
}

const ChatManager: React.FC<ChatManagerProps> = ({
  onQuoteReceived,
  onResponseReceived,
  onStateChange,
}) => {
  const wsRef = useRef<WebSocket | null>(null);
  const [visitorId, setVisitorId] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);

  // Generate a simple visitor ID (in production, this would be a proper fingerprint)
  useEffect(() => {
    const generateVisitorId = () => {
      return 'visitor_' + Math.random().toString(36).substr(2, 9);
    };

    setVisitorId(generateVisitorId());
  }, []);

  // WebSocket connection management
  useEffect(() => {
    if (!visitorId) return;

    const connectWebSocket = () => {
      try {
        // Dynamic WebSocket URL based on environment
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = window.location.hostname === 'localhost' ? ':8000' : '';
        const wsUrl = `${protocol}//${host}${port}/ws/chat?visitor_id=${visitorId}`;
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
        };

        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        wsRef.current.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);

          // Attempt to reconnect after a delay
          setTimeout(() => {
            connectWebSocket();
          }, 3000);
        };

        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [visitorId]);

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'conversation_quote':
        onQuoteReceived(data.quote);
        break;

      case 'message_received':
        // User message was successfully received
        onStateChange('receiving');
        break;

      case 'ai_response_chunk':
        // Streaming chunk received - accumulate response
        onResponseReceived(data.content);
        onStateChange('responding');
        break;
        
      case 'ai_response_complete':
        // Streaming complete - final state change
        onStateChange('responding');
        break;

      case 'ai_response':
        // Non-streaming response - set content first, then trigger animation
        onResponseReceived(data.message.content);
        // Longer delay to ensure DOM is updated and animation is visible
        setTimeout(() => {
          onStateChange('responding');
        }, 300);
        break;

      case 'error':
        console.error('WebSocket error:', data.error);
        onStateChange('idle');
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const sendMessage = (message: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      try {
        // Detect if we're on mobile (width < 999px)
        const isMobile = window.innerWidth < 999;

        const messageData = {
          type: 'user_message',
          content: message,
          is_mobile: isMobile,
        };

        wsRef.current.send(JSON.stringify(messageData));
        onStateChange('sending');
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  };

  // Expose sendMessage function to parent via ref or callback
  useEffect(() => {
    // Store sendMessage in a way the parent can access it
    (window as any).chatManager = { sendMessage };

    return () => {
      delete (window as any).chatManager;
    };
  }, []);

  return (
    <>
      <MessageDebouncer isConnected={isConnected} onSendMessage={sendMessage} />

      {/* Connection status indicator - commented out for cleaner UI */}
      {/* 
      {process.env.NODE_ENV === 'development' && (
        <div className="connection-status">
          Status: {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      )}
      */}
    </>
  );
};

export default ChatManager;
