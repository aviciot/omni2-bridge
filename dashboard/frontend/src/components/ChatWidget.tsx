"use client";

"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Message {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  toolsUsed?: string[];
  toolCalls?: number;
  reaction?: string;
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDebugMode, setIsDebugMode] = useState(false);
  const [useWebSocket, setUseWebSocket] = useState(true); // NEW: Toggle for WebSocket vs SSE
  const [ws, setWs] = useState<WebSocket | null>(null); // NEW: WebSocket connection
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [size, setSize] = useState({ width: 450, height: 650 });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const clearChat = () => {
    if (confirm("Clear all messages?")) {
      setMessages([]);
    }
  };

  const copyMessage = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const exportChat = () => {
    const chatText = messages
      .map((m) => `[${m.timestamp.toLocaleString()}] ${m.sender === "user" ? "You" : "OMNI2"}: ${m.text}`)
      .join("\n\n");
    const blob = new Blob([chatText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `omni2-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const addReaction = (messageId: string, reaction: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, reaction } : m))
    );
  };

  const suggestedPrompts = [
    "Show me database statistics",
    "List all MCP servers",
    "Check system health",
    "Show recent activity",
  ];

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current && !isMinimized) {
      inputRef.current.focus();
    }
  }, [isOpen, isMinimized]);

  // NEW: WebSocket connection management
  useEffect(() => {
    if (!isOpen || !useWebSocket) {
      if (ws) {
        ws.close();
        setWs(null);
      }
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) return;
    
    const wsUrl = `ws://localhost:8500/ws/chat?token=${token}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      alert('✅ WebSocket Connected!');
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('[ChatWidget] Message received:', data.type, data.text ? `"${data.text}"` : '');
      
      if (data.type === "token") {
        // Append token to current message
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          console.log('[ChatWidget] Last message:', lastMsg ? `id=${lastMsg.id}, sender=${lastMsg.sender}` : 'NONE');
          if (lastMsg && lastMsg.sender === "bot" && lastMsg.id.startsWith("bot-")) {
            console.log('[ChatWidget] Appending to existing message');
            return prev.map((m, i) => i === prev.length - 1 ? { ...m, text: m.text + data.text } : m);
          } else {
            console.log('[ChatWidget] Creating new message');
            return [...prev, {
              id: `bot-${Date.now()}`,
              text: data.text,
              sender: "bot" as const,
              timestamp: new Date(),
            }];
          }
        });
      } else if (data.type === "done") {
        setIsTyping(false);
      } else if (data.type === "error") {
        setMessages((prev) => [...prev, {
          id: `error-${Date.now()}`,
          text: `❌ Error: ${data.error}`,
          sender: "bot" as const,
          timestamp: new Date(),
        }]);
        setIsTyping(false);
      }
    };

    socket.onerror = (error) => {
      alert('❌ WebSocket Error!');
    };

    socket.onclose = (event) => {
      alert(`🔌 WebSocket Closed - Code: ${event.code}, Reason: ${event.reason}`);
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, [isOpen, useWebSocket]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      text: input,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const messageText = input;
    setInput("");
    setIsTyping(true);

    // WebSocket mode
    if (useWebSocket && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "message",
        text: messageText
      }));
      return;
    }

    // SSE mode
    const startTime = Date.now();
    let accumulatedText = "";
    let botMessageId = `bot-${Date.now()}`;

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          message: input,
          user_id: "admin",
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("event: token")) {
            continue;
          }
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.text) {
                accumulatedText += data.text;
                setMessages((prev) => {
                  const existing = prev.find(m => m.id === botMessageId);
                  if (existing) {
                    return prev.map(m => m.id === botMessageId ? { ...m, text: accumulatedText } : m);
                  } else {
                    return [...prev, {
                      id: botMessageId,
                      text: accumulatedText,
                      sender: "bot" as const,
                      timestamp: new Date(),
                    }];
                  }
                });
              }
            } catch (e) {
              // Ignore parse errors for incomplete chunks
            }
          }
          if (line.startsWith("event: done")) {
            const nextLine = lines[lines.indexOf(line) + 1];
            if (nextLine?.startsWith("data: ")) {
              try {
                const result = JSON.parse(nextLine.slice(6));
                setMessages((prev) =>
                  prev.map(m => m.id === botMessageId ? {
                    ...m,
                    toolsUsed: result.tools_used || [],
                    toolCalls: result.tool_calls || 0,
                  } : m)
                );
              } catch (e) {
                // Ignore
              }
            }
          }
        }
      }
    } catch (error: any) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        text: `❌ Error: ${error.message || "Failed to send message"}`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleResize = (direction: "width" | "height", delta: number) => {
    setSize((prev) => {
      const newSize = { ...prev };
      if (direction === "width") {
        newSize.width = Math.max(350, Math.min(800, prev.width + delta));
      } else {
        newSize.height = Math.max(400, Math.min(900, prev.height + delta));
      }
      return newSize;
    });
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-br from-purple-600 to-purple-800 text-white rounded-full shadow-2xl hover:shadow-purple-500/50 transition-all duration-300 hover:scale-110 z-50 flex items-center justify-center group"
        aria-label="Open chat"
      >
        <svg
          className="w-7 h-7 group-hover:scale-110 transition-transform"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white animate-pulse"></span>
      </button>
    );
  }

  return (
    <div
      className="fixed bottom-6 right-6 bg-white rounded-2xl shadow-2xl flex flex-col z-50 border border-gray-200 overflow-hidden"
      style={{ width: `${size.width}px`, height: isMinimized ? "auto" : `${size.height}px` }}
    >
      {/* Header */}
      <div
        className="bg-gradient-to-r from-purple-600 via-purple-700 to-purple-800 text-white p-4 flex items-center justify-between shadow-lg"
      >
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-400 rounded-full border-2 border-purple-700"></span>
            </div>
            <div>
              <h3 className="font-bold text-sm">OMNI2 Assistant</h3>
              <p className="text-xs text-purple-100">Full MCP Access</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setUseWebSocket(!useWebSocket)}
              className={`text-white/80 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg ${useWebSocket ? "bg-white/20" : ""}`}
              title={useWebSocket ? "Using WebSocket (conversation tracking)" : "Using SSE (no conversation tracking)"}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            <button
              onClick={() => setIsDebugMode(!isDebugMode)}
              className={`text-white/80 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg ${isDebugMode ? "bg-white/20" : ""}`}
              title="Toggle debug mode"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </button>
            <button onClick={exportChat} className="text-white/80 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg" title="Export chat">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            <button onClick={clearChat} className="text-white/80 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg" title="Clear chat">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
            <button onClick={() => setIsMinimized(!isMinimized)} className="text-white/80 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg" title={isMinimized ? "Maximize" : "Minimize"}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {isMinimized ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                )}
              </svg>
            </button>
            <button onClick={() => setIsOpen(false)} className="text-white/80 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg" aria-label="Close chat">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-gray-50 to-white">
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-fade-in group`}>
                  <div className="flex flex-col max-w-[85%]">
                    <div className={`rounded-2xl px-4 py-3 shadow-md relative ${message.sender === "user" ? "bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-br-sm" : "bg-white text-gray-800 border border-gray-200 rounded-bl-sm"}`}>
                      <div className="text-sm leading-relaxed prose prose-sm max-w-none">
                        <ReactMarkdown
                          components={{
                            code({ node, inline, className, children, ...props }: any) {
                              const match = /language-(\w+)/.exec(className || "");
                              return !inline && match ? (
                                <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                                  {String(children).replace(/\n$/, "")}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={`${className} bg-gray-100 px-1 rounded`} {...props}>
                                  {children}
                                </code>
                              );
                            },
                          }}
                        >
                          {message.text}
                        </ReactMarkdown>
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <span className={`text-[10px] ${message.sender === "user" ? "text-purple-200" : "text-gray-400"}`}>
                          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                        <div className="flex items-center space-x-2">
                          {message.sender === "bot" && (
                            <>
                              <button onClick={() => addReaction(message.id, "👍")} className="opacity-0 group-hover:opacity-100 transition-opacity text-xs hover:scale-125" title="Good response">
                                {message.reaction === "👍" ? "👍" : "👍🏻"}
                              </button>
                              <button onClick={() => addReaction(message.id, "👎")} className="opacity-0 group-hover:opacity-100 transition-opacity text-xs hover:scale-125" title="Bad response">
                                {message.reaction === "👎" ? "👎" : "👎🏻"}
                              </button>
                            </>
                          )}
                          <button onClick={() => copyMessage(message.text)} className={`opacity-0 group-hover:opacity-100 transition-opacity text-[10px] ${message.sender === "user" ? "text-purple-200 hover:text-white" : "text-gray-400 hover:text-gray-600"}`} title="Copy message">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                    {message.sender === "bot" && message.toolsUsed && message.toolsUsed.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1 ml-1">
                        {message.toolsUsed.map((tool, idx) => (
                          <span key={idx} className="text-[9px] px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full border border-purple-200" title="MCP tool used">
                            🔧 {tool}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start animate-fade-in">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-md">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                      <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggested Prompts */}
            {messages.length <= 1 && (
              <div className="px-4 py-2 bg-gray-50 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-2">Suggested prompts:</p>
                <div className="flex flex-wrap gap-2">
                  {suggestedPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInput(prompt)}
                      className="text-xs px-3 py-1.5 bg-white border border-purple-200 text-purple-700 rounded-full hover:bg-purple-50 transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="p-4 bg-white border-t border-gray-200">
              <div className="flex space-x-2 items-end">
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask OMNI2 anything..."
                    disabled={isTyping}
                    className="w-full px-4 py-3 pr-12 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed text-gray-900 placeholder-gray-400 transition-all"
                    style={{ backgroundColor: "white", color: "black" }}
                  />
                  {input && (
                    <button onClick={() => setInput("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
                <button
                  onClick={handleSend}
                  disabled={isTyping || !input.trim()}
                  className="bg-gradient-to-r from-purple-600 to-purple-700 text-white p-3 rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed shadow-lg hover:shadow-xl disabled:shadow-none transform hover:scale-105 disabled:scale-100"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
              <p className="text-[10px] text-gray-400 mt-2 text-center">
                🔒 <span className="font-semibold text-purple-600">Admin</span> • 
                {useWebSocket ? (
                  ws && ws.readyState === WebSocket.OPEN ? 
                    <span className="text-green-600">✓ WebSocket Connected</span> : 
                    <span className="text-orange-600">⚠ WebSocket Connecting...</span>
                ) : (
                  <span className="text-blue-600">SSE Mode</span>
                )}
              </p>
            </div>
          </>
        )}

        {/* Resize handles */}
        {!isMinimized && (
          <>
            <div
              className="absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize hover:bg-purple-300 transition-colors opacity-0 hover:opacity-100"
              onMouseDown={(e) => {
                e.preventDefault();
                const startX = e.clientX;
                const startWidth = size.width;
                const handleMouseMove = (e: MouseEvent) => handleResize("width", e.clientX - startX);
                const handleMouseUp = () => {
                  document.removeEventListener("mousemove", handleMouseMove);
                  document.removeEventListener("mouseup", handleMouseUp);
                };
                document.addEventListener("mousemove", handleMouseMove);
                document.addEventListener("mouseup", handleMouseUp);
              }}
            />
            <div
              className="absolute left-0 right-0 bottom-0 h-2 cursor-ns-resize hover:bg-purple-300 transition-colors opacity-0 hover:opacity-100"
              onMouseDown={(e) => {
                e.preventDefault();
                const startY = e.clientY;
                const startHeight = size.height;
                const handleMouseMove = (e: MouseEvent) => handleResize("height", e.clientY - startY);
                const handleMouseUp = () => {
                  document.removeEventListener("mousemove", handleMouseMove);
                  document.removeEventListener("mouseup", handleMouseUp);
                };
                document.addEventListener("mousemove", handleMouseMove);
                document.addEventListener("mouseup", handleMouseUp);
              }}
            />
          </>
        )}

        <style jsx>{`
          @keyframes fade-in {
            from {
              opacity: 0;
              transform: translateY(10px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
          .animate-fade-in {
            animation: fade-in 0.3s ease-out;
          }
          .prose code {
            color: inherit;
          }
        `}</style>
      </div>
  );
}
