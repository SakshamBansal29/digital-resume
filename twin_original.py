'use client';

import { useState, useRef, useEffect } from 'react';
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
            //const response = await fetch('https://t3ufutghx7.execute-api.us-east-1.amazonaws.com/chat', {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: input,
                    email_id: email,
                    //session_id: sessionId || undefined,
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
            
            // if (!sessionId) {
            //     setSessionId(data.session_id);
            // }


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
            //const res = await fetch('https://t3ufutghx7.execute-api.us-east-1.amazonaws.com/chat', {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: `My email is: ${email}`,
                    email_id: email,
                    // session_id: sessionId || undefined,
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

    // Only work on browser
    // useEffect(() => {
    //     if (!emailSubmitted) return; // only after email is submitted
      
    //     const handleBeforeUnload = (event: BeforeUnloadEvent) => {
    //       if (!email) return;
    //       //if (!sessionId) return;  
    //       // send session_id to backend on window close
    //       const payload = JSON.stringify({ session_id: email });
    //       //const payload = JSON.stringify({ session_id: sessionId }); 
    //       navigator.sendBeacon(
    //         //'https://t3ufutghx7.execute-api.us-east-1.amazonaws.com/chat-close',
    //         `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat-close`,
    //         payload
    //       );
    //     };
      
    //     window.addEventListener("beforeunload", handleBeforeUnload);
      
    //     return () => {
    //       window.removeEventListener("beforeunload", handleBeforeUnload);
    //     };
    //   }, [emailSubmitted, email]);


    // Only work on change in tab 
    // useEffect(() => {
    //     if (!emailSubmitted || !email) return;

    //     let sentClose = false;

    //     const sendCloseSignal = () => {
    //         if (sentClose) return;
    //         sentClose = true;

    //         const payload = JSON.stringify({ 
    //             session_id: sessionId || email,
    //             email_id: email 
    //         });
            
    //         navigator.sendBeacon(
    //             `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat-close`,
    //             payload
    //         );
    //     };

    //     // Mobile: app switch, tab background
    //     document.addEventListener('visibilitychange', () => {
    //         if (document.visibilityState === 'hidden') {
    //             sendCloseSignal();
    //         }
    //     });

    //     // Mobile: tab close, back button
    //     window.addEventListener('pagehide', sendCloseSignal);

    //     // Desktop: tab/window close
    //     window.addEventListener('beforeunload', sendCloseSignal);

    //     // Mobile fallback
    //     window.addEventListener('unload', sendCloseSignal);

    //     return () => {
    //         document.removeEventListener('visibilitychange', () => {});
    //         window.removeEventListener('pagehide', sendCloseSignal);
    //         window.removeEventListener('beforeunload', sendCloseSignal);
    //         window.removeEventListener('unload', sendCloseSignal);
    //     };
    // }, [emailSubmitted, email, sessionId]);
    
    

    //     if (!emailSubmitted) return; // only after email is submitted
      
    //     const handleBeforeUnload = (event: BeforeUnloadEvent) => {
    //       if (!email) return;
    //       //if (!sessionId) return;  
    //       // send session_id to backend on window close
    //       const payload = JSON.stringify({ session_id: email });
    //       //const payload = JSON.stringify({ session_id: sessionId }); 
    //       navigator.sendBeacon(
    //         //'https://t3ufutghx7.execute-api.us-east-1.amazonaws.com/chat-close',
    //         `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat-close`,
    //         payload
    //       );
    //     };
      
    //     window.addEventListener("beforeunload", handleBeforeUnload);
      
    //     return () => {
    //       window.removeEventListener("beforeunload", handleBeforeUnload);
    //     };
    //   }, [emailSubmitted, email]);
    useEffect(() => {
        if (!emailSubmitted || !email) return;

        let sentClose = false;

        const sendCloseSignal = () => {
            if (sentClose) return;
            sentClose = true;

            const payload = JSON.stringify({
            session_id: sessionId || email,
            email_id: email,
            });

            const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/chat-close`;

            // Prefer sendBeacon when available
            if (navigator.sendBeacon) {
            navigator.sendBeacon(url, payload);
            } else {
            // Fallback for older browsers
            fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: payload,
                keepalive: true,
            }).catch(() => {});
            }
        };

        // Use named handlers so removal works correctly
        const handleVisibilityChange = () => {
            // Fires when tab becomes hidden (tab change, app switch, etc.)
            if (document.visibilityState === "hidden") {
                sendCloseSignal();
            } else {
                sentClose = false; 
            }
        };

        const handlePageHide = () => {
            // Fires on tab close, navigation away, some back/forward actions
            sendCloseSignal();
        };

        const handleBeforeUnload = (event: BeforeUnloadEvent) => {
          if (!email) return;
          //if (!sessionId) return;  
          const payload = JSON.stringify({ session_id: email });
          //const payload = JSON.stringify({ session_id: sessionId }); 
          navigator.sendBeacon(
            //'https://t3ufutghx7.execute-api.us-east-1.amazonaws.com/chat-close',
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat-close`,
            payload
          );
        };

        // Attach listeners
        document.addEventListener("visibilitychange", handleVisibilityChange);
        window.addEventListener("pagehide", handlePageHide);
        window.addEventListener("beforeunload", handleBeforeUnload);

        return () => {
            document.removeEventListener("visibilitychange", handleVisibilityChange);
            window.removeEventListener("pagehide", handlePageHide);
            window.removeEventListener("beforeunload", handleBeforeUnload);
        };
    }, [emailSubmitted, email, sessionId]);



    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (!emailSubmitted) return;
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };
    

    return (
        <div className="flex flex-col h-full bg-gray-50 rounded-lg shadow-lg">

            {/* Header */}
            <div className="bg-gradient-to-r from-slate-700 to-slate-800 text-white p-4 rounded-t-lg">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Bot className="w-6 h-6" />
                    AI Assistance Chat
                </h2>
                {/* <p className="text-sm text-slate-300 mt-1">Your AI course companion</p> */}
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
                            onChange={(e) => setInput(e.target.value)}
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
