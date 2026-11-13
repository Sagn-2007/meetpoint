import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage } from '../types/session';

export type ConnectionStatus = 'connected' | 'connecting' | 'reconnecting' | 'disconnected' | 'error';

interface UseSessionWebSocketProps {
  sessionId: string | null;
  token: string | null;
  onMessage: (message: WebSocketMessage) => void;
  enabled?: boolean;
}

export function useSessionWebSocket({
  sessionId,
  token,
  onMessage,
  enabled = true,
}: UseSessionWebSocketProps) {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const onMessageRef = useRef(onMessage);

  // Keep callback reference updated
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (!sessionId || !token || !enabled) return;

    // Build WS URL without raw tokens in query string
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsBase = apiBase.replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/api/v1/sessions/${sessionId}/ws`;

    setStatus(reconnectAttemptsRef.current === 0 ? 'connecting' : 'reconnecting');

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        // First-message authentication handshake to keep credentials out of server access logs
        ws.send(JSON.stringify({ type: 'authenticate', token }));
        setStatus('connected');
        reconnectAttemptsRef.current = 0;

        // Start ping heartbeat every 25 seconds
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.type === 'pong') return; // heartbeat response
          onMessageRef.current(parsed);
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      };

      ws.onerror = (err) => {
        console.warn('WebSocket encountered error:', err);
      };

      ws.onclose = (event) => {
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // If closed intentionally or unrecoverable (4003 unauthorized / 4004 not found)
        if (event.code === 4003 || event.code === 4004 || event.code === 1000) {
          setStatus('disconnected');
          return;
        }

        // Attempt reconnection with exponential backoff up to 10 seconds
        setStatus('reconnecting');
        const timeout = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 10000);
        reconnectAttemptsRef.current += 1;

        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, timeout);
      };
    } catch (e) {
      console.error('Error initiating WebSocket:', e);
      setStatus('error');
    }
  }, [sessionId, token, enabled]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { status };
}
