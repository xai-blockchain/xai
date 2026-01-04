import { useState, useEffect, useCallback, useRef } from 'react';
import type { Block, Transaction, AITask, WebSocketMessage } from '../types';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseWebSocketOptions {
  url?: string;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  onBlock?: (block: Block) => void;
  onTransaction?: (transaction: Transaction) => void;
  onAITask?: (task: AITask) => void;
  onError?: (error: Error) => void;
}

interface UseWebSocketReturn {
  status: ConnectionStatus;
  lastMessage: WebSocketMessage | null;
  latestBlock: Block | null;
  latestTransaction: Transaction | null;
  latestAITask: AITask | null;
  recentBlocks: Block[];
  recentTransactions: Transaction[];
  recentAITasks: AITask[];
  connect: () => void;
  disconnect: () => void;
  send: (message: string) => void;
}

const DEFAULT_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws/live`;
const MAX_RECENT_ITEMS = 10;

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = DEFAULT_URL,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    onBlock,
    onTransaction,
    onAITask,
    onError,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [latestBlock, setLatestBlock] = useState<Block | null>(null);
  const [latestTransaction, setLatestTransaction] = useState<Transaction | null>(null);
  const [latestAITask, setLatestAITask] = useState<AITask | null>(null);
  const [recentBlocks, setRecentBlocks] = useState<Block[]>([]);
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [recentAITasks, setRecentAITasks] = useState<AITask[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimeoutRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isManualDisconnectRef = useRef(false);

  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }
    heartbeatTimeoutRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      // Handle pong response
      if (event.data === 'pong') {
        return;
      }

      const message: WebSocketMessage = JSON.parse(event.data);
      setLastMessage(message);

      switch (message.type) {
        case 'block': {
          const block = message.data as Block;
          setLatestBlock(block);
          setRecentBlocks(prev => [block, ...prev.slice(0, MAX_RECENT_ITEMS - 1)]);
          onBlock?.(block);
          break;
        }
        case 'transaction': {
          const tx = message.data as Transaction;
          setLatestTransaction(tx);
          setRecentTransactions(prev => [tx, ...prev.slice(0, MAX_RECENT_ITEMS - 1)]);
          onTransaction?.(tx);
          break;
        }
        case 'ai_task': {
          const task = message.data as AITask;
          setLatestAITask(task);
          setRecentAITasks(prev => [task, ...prev.slice(0, MAX_RECENT_ITEMS - 1)]);
          onAITask?.(task);
          break;
        }
        case 'error': {
          console.error('WebSocket error message:', message.data);
          onError?.(new Error(String(message.data)));
          break;
        }
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  }, [onBlock, onTransaction, onAITask, onError]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    isManualDisconnectRef.current = false;
    setStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('connected');
        reconnectCountRef.current = 0;
        startHeartbeat();
        console.log('WebSocket connected');
      };

      ws.onmessage = handleMessage;

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setStatus('error');
        onError?.(new Error('WebSocket connection error'));
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setStatus('disconnected');
        clearTimeouts();

        // Attempt reconnection if not manually disconnected
        if (!isManualDisconnectRef.current && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          console.log(`Reconnecting... attempt ${reconnectCountRef.current}/${reconnectAttempts}`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setStatus('error');
      onError?.(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [url, reconnectAttempts, reconnectInterval, handleMessage, startHeartbeat, clearTimeouts, onError]);

  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
    clearTimeouts();
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, [clearTimeouts]);

  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  return {
    status,
    lastMessage,
    latestBlock,
    latestTransaction,
    latestAITask,
    recentBlocks,
    recentTransactions,
    recentAITasks,
    connect,
    disconnect,
    send,
  };
}

// Connection status indicator component helper
export function getStatusColor(status: ConnectionStatus): string {
  switch (status) {
    case 'connected':
      return 'bg-green-500';
    case 'connecting':
      return 'bg-yellow-500';
    case 'error':
      return 'bg-red-500';
    default:
      return 'bg-gray-500';
  }
}

export function getStatusText(status: ConnectionStatus): string {
  switch (status) {
    case 'connected':
      return 'Live';
    case 'connecting':
      return 'Connecting...';
    case 'error':
      return 'Error';
    default:
      return 'Offline';
  }
}
