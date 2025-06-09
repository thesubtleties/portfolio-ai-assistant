import { useEffect, useRef, useState } from 'react';

interface MessageDebouncerProps {
  isConnected: boolean;
  onSendMessage: (message: string) => Promise<void>;
  debounceTime?: number; // Time to wait after AI response before allowing new messages
}

const MessageDebouncer: React.FC<MessageDebouncerProps> = ({
  isConnected,
  onSendMessage,
  debounceTime = 1500, // 1.5 seconds after AI response (reduced from 2s)
}) => {
  const [isDebouncing, setIsDebouncing] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  const sendMessage = async (message: string): Promise<boolean> => {
    // Check if we can send (connected and not debouncing)
    if (!isConnected || isDebouncing) {
      setPendingMessage(message);
      return false;
    }

    try {
      setIsDebouncing(true);
      await onSendMessage(message);

      // Start debounce timer after sending
      debounceTimeoutRef.current = setTimeout(() => {
        setIsDebouncing(false);

        // If there's a pending message, send it
        if (pendingMessage) {
          const nextMessage = pendingMessage;
          setPendingMessage(null);
          // Use setTimeout to avoid recursion issues
          setTimeout(() => sendMessage(nextMessage), 100);
        }
      }, debounceTime);

      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      setIsDebouncing(false);
      return false;
    }
  };

  // Expose sendMessage function globally for the terminal input
  useEffect(() => {
    (window as any).sendMessage = sendMessage;

    return () => {
      delete (window as any).sendMessage;
    };
  }, [isConnected, isDebouncing, pendingMessage]);

  // Visual indicator for debouncing state - commented out for cleaner UI
  /*
  if (process.env.NODE_ENV === 'development') {
    return (
      <div className="message-debouncer-status">
        <div>Debouncing: {isDebouncing ? 'Yes' : 'No'}</div>
        {pendingMessage && <div>Pending: {pendingMessage.substring(0, 20)}...</div>}
      </div>
    );
  }
  */

  return null;
};

export default MessageDebouncer;
