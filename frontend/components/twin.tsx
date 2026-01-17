'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

export default function Twin() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string>('');
    const [lastActivity, setLastActivity] = useState(Date.now());
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const [email, setEmail] = useState("");
    const [emailError, setEmailError] = useState("");
    const [emailSubmitted, setEmailSubmitted] = useState(false);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Update last activity on any user interaction
    const updateActivity = useCallback(() => {
        setLastActivity(Date.now());
    }, []);

    // --------------------------------------------
    // Validate an email
    // --------------------------------------------
    const isValidEmail = (email: string) => {
        return /\S+@\S+\.\S+/.test(email);
    };

    // --------------------------------------------
    // SEND NORMAL CHAT MESSAGE (after email)
    // --------------------------------------------
    const sendMessage = async () => {
        if (!input.trim() || isLoading) return;

        updateActivity();

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: input,
                    email_id: email,
                    session_id: sessionId || email,
                }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error("Backend error:", errorText);
                throw new Error("Failed to send message");
            }

            const data = await response.json();
            console.log("📧 OLD email state:", email);
            console.log("🔑 NEW sessionId from backend:", data.session_id);
            console.log("📱 Frontend will send next:", {email_id: email, session_id: data.session_id});
            setSessionId(data.session_id);
            
            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.response,
                timestamp: new Date(),
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Error:', error);

            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    // --------------------------------------------
    // SEND EMAIL AS FIRST MESSAGE
    // --------------------------------------------
    const submitEmail = async () => {
        setEmailError("");

        if (!email.trim()) {
            setEmailError("Please enter your email.");
            return;
        }

        if (!isValidEmail(email)) {
            setEmailError("Please enter a valid email address.");
            return;
        }

        updateActivity();
        setEmailSubmitted(true);

        // Store as initial message
        const emailMsg: Message = {
            id: Date.now().toString(),
            role: "user",
            content: `My email is: ${email}`,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, emailMsg]);

        // Send to backend as first LLM interaction
        setIsLoading(true);
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: `My email is: ${email}`,
                    email_id: email,
                    session_id: sessionId || email,
                }),
            });

            if (!res.ok) {
                const errorText = await res.text();
                console.error("Backend error:", errorText);
                throw new Error("Failed first email message");
            }

            const data = await res.json();
            setSessionId(data.session_id);

            // Assistant reply
            const assistantMsg: Message = {
                id: (Date.now() + 2).toString(),
                role: "assistant",
                content: data.response,
                timestamp: new Date(),
            };

            setMessages(prev => [...prev, assistantMsg]);
        } catch (err) {
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    // --------------------------------------------
    // IDLE TIMEOUT - 60 minutes
    // --------------------------------------------
    useEffect(() => {
        if (!emailSubmitted || !email) return;

        const IDLE_TIMEOUT = 60 * 60 * 1000; // 60 minutes
        let idleTimeoutId: NodeJS.Timeout;

        const checkIdle = () => {
            const now = Date.now();
            if (now - lastActivity > IDLE_TIMEOUT) {
                sendChatClose();
                clearTimeout(idleTimeoutId);
            } else {
                // Reschedule check
                idleTimeoutId = setTimeout(checkIdle, 60000); // Check every minute
            }
        };

        idleTimeoutId = setTimeout(checkIdle, 60000);
        return () => clearTimeout(idleTimeoutId);
    }, [emailSubmitted, email, lastActivity, sessionId]);

    // --------------------------------------------
    // Send chat-close signal
    // --------------------------------------------
    const sendChatClose = () => {
        if (!email) return;

        const payload = JSON.stringify({
            session_id: sessionId || email,
            email_id: email,
        });

        const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/chat-close`;

        if (navigator.sendBeacon) {
            navigator.sendBeacon(url, payload);
        } else {
            fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: payload,
                keepalive: true,
            }).catch(() => {});
        }
    };

    // --------------------------------------------
    // WINDOW CLOSE HANDLERS (laptop) & MOBILE TAB CLOSE
    // --------------------------------------------
    useEffect(() => {
        if (!emailSubmitted || !email) return;

        const handleBeforeUnload = (event: BeforeUnloadEvent) => {
            sendChatClose();
        };

        const handlePageHide = () => {
            sendChatClose();
        };

        // Laptop: window/tab close
        // Mobile: tab close (pagehide fires on tab close, not app switch)
        window.addEventListener("beforeunload", handleBeforeUnload);
        window.addEventListener("pagehide", handlePageHide);

        return () => {
            window.removeEventListener("beforeunload", handleBeforeUnload);
            window.removeEventListener("pagehide", handlePageHide);
        };
    }, [emailSubmitted, email, sessionId]);

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (!emailSubmitted) return;
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Add activity tracking to input events
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        updateActivity();
        setInput(e.target.value);
    };

    return (
        <div 
            className="flex flex-col h-full bg-gray-50 rounded-lg shadow-lg"
            onMouseMove={updateActivity}
            onKeyDown={updateActivity}
            onScroll={updateActivity}
        >
            {/* Header */}
            <div className="bg-gradient-to-r from-slate-700 to-slate-800 text-white p-4 rounded-t-lg">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Bot className="w-6 h-6" />
                    AI Assistance Chat
                </h2>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        {message.role === 'assistant' && (
                            <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center">
                                    <Bot className="w-5 h-5 text-white" />
                                </div>
                            </div>
                        )}

                        <div
                            className={`max-w-[70%] rounded-lg p-3 ${message.role === 'user'
                                ? 'bg-slate-700 text-white'
                                : 'bg-white border border-gray-200 text-gray-800'
                                }`}
                        >
                            <div className="max-w-none leading-relaxed text-sm">
                                <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                                    {message.content}
                                </ReactMarkdown>
                            </div>
                            <p className="text-xs mt-1 text-gray-500">
                                {message.timestamp.toLocaleTimeString()}
                            </p>
                        </div>

                        {message.role === 'user' && (
                            <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                                    <User className="w-5 h-5 text-white" />
                                </div>
                            </div>
                        )}
                    </div>
                ))}

                {isLoading && (
                    <div className="flex gap-3 justify-start">
                        <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center">
                            <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div className="bg-white border border-gray-200 rounded-lg p-3">
                            <div className="flex space-x-2">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-200 p-4 bg-white rounded-b-lg">
                {!emailSubmitted ? (
                    <div className="flex flex-col gap-2">
                        <input
                            type="email"
                            placeholder="Enter your email to start..."
                            value={email}
                            onChange={(e) => {
                                updateActivity();
                                setEmail(e.target.value);
                                setEmailError("");
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-800"
                        />

                        {emailError && (
                            <p className="text-red-600 text-sm">{emailError}</p>
                        )}

                        <button
                            onClick={submitEmail}
                            className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800"
                        >
                            Start Chat
                        </button>
                    </div>
                ) : (
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={handleInputChange}
                            onKeyDown={handleKeyPress}
                            placeholder="Type your message..."
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-800"
                            disabled={isLoading}
                        />
                        <button
                            onClick={sendMessage}
                            disabled={!input.trim() || isLoading}
                            className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
