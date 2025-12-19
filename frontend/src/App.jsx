import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import Settings from './components/Settings';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content, images = []) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI (with images if present)
      const userMessage = { role: 'user', content };
      if (images.length > 0) {
        userMessage.images = images;
      }
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming (including images)
      await api.sendMessageStream(currentConversationId, content, images, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage1 = true;
              // Initialize stage1 as empty array and track pending models
              lastMsg.stage1 = [];
              lastMsg.stage1PendingModels = event.models || [];
              return { ...prev, messages };
            });
            break;

          case 'stage1_response':
            // Handle individual model response as it arrives
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              
              // Remove this model from pending list
              const modelName = event.data.model;
              lastMsg.stage1PendingModels = (lastMsg.stage1PendingModels || [])
                .filter(m => m !== modelName);
              
              // Add response if it didn't fail and isn't already present (prevent duplicates)
              if (!event.data.failed) {
                const existingModels = (lastMsg.stage1 || []).map(r => r.model);
                if (!existingModels.includes(modelName)) {
                  lastMsg.stage1 = [...(lastMsg.stage1 || []), event.data];
                }
              }
              
              return { ...prev, messages };
            });
            break;

          case 'stage1_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              // Final stage1 data is already built up, but use this as authoritative source
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              lastMsg.stage1PendingModels = [];
              return { ...prev, messages };
            });
            break;

          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage2 = true;
              // Initialize stage2 as empty array and track pending models
              lastMsg.stage2 = [];
              lastMsg.stage2PendingModels = event.models || [];
              // Store label_to_model early so we can use it as rankings come in
              if (event.metadata?.label_to_model) {
                lastMsg.metadata = { ...lastMsg.metadata, label_to_model: event.metadata.label_to_model };
              }
              return { ...prev, messages };
            });
            break;

          case 'stage2_response':
            // Handle individual model ranking as it arrives
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              
              // Remove this model from pending list
              const modelName = event.data.model;
              lastMsg.stage2PendingModels = (lastMsg.stage2PendingModels || [])
                .filter(m => m !== modelName);
              
              // Add ranking if it didn't fail (prevent duplicates)
              if (!event.data.failed) {
                const existingModels = (lastMsg.stage2 || []).map(r => r.model);
                if (!existingModels.includes(modelName)) {
                  lastMsg.stage2 = [...(lastMsg.stage2 || []), event.data];
                }
              }
              
              return { ...prev, messages };
            });
            break;

          case 'stage2_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              // Final stage2 data
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading.stage2 = false;
              lastMsg.stage2PendingModels = [];
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage3 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage3_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage3 = event.data;
              lastMsg.loading.stage3 = false;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />
      <Settings />
    </div>
  );
}

export default App;
