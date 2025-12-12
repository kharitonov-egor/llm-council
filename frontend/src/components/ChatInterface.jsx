import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

// Max file size: 10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024;
// Max images per message
const MAX_IMAGES = 4;
// Allowed image types
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const [images, setImages] = useState([]);
  const [lightboxImage, setLightboxImage] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const processFile = (file) => {
    return new Promise((resolve, reject) => {
      if (!ALLOWED_TYPES.includes(file.type)) {
        reject(new Error(`Invalid file type: ${file.type}. Allowed: PNG, JPEG, GIF, WebP`));
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        reject(new Error(`File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB. Max: 10MB`));
        return;
      }

      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  };

  const addImages = async (files) => {
    const newImages = [];
    for (const file of files) {
      if (images.length + newImages.length >= MAX_IMAGES) {
        alert(`Maximum ${MAX_IMAGES} images allowed per message`);
        break;
      }
      try {
        const dataUrl = await processFile(file);
        newImages.push(dataUrl);
      } catch (err) {
        alert(err.message);
      }
    }
    if (newImages.length > 0) {
      setImages((prev) => [...prev, ...newImages]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files?.length) {
      addImages(Array.from(e.target.files));
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  };

  const handlePaste = async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const imageFiles = [];
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) imageFiles.push(file);
      }
    }

    if (imageFiles.length > 0) {
      e.preventDefault();
      addImages(imageFiles);
    }
  };

  const removeImage = (index) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((input.trim() || images.length > 0) && !isLoading) {
      onSendMessage(input, images);
      setInput('');
      setImages([]);
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    {msg.images && msg.images.length > 0 && (
                      <div className="message-images">
                        {msg.images.map((img, imgIndex) => (
                          <img
                            key={imgIndex}
                            src={img}
                            alt={`Attached ${imgIndex + 1}`}
                            className="message-image"
                            onClick={() => setLightboxImage(img)}
                            title="Click to enlarge"
                          />
                        ))}
                      </div>
                    )}
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">LLM Council</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && !msg.stage1?.length && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {(msg.stage1?.length > 0 || msg.stage1PendingModels?.length > 0) && (
                    <Stage1 
                      responses={msg.stage1 || []} 
                      pendingModels={msg.stage1PendingModels || []}
                      isLoading={msg.loading?.stage1}
                    />
                  )}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && !msg.stage2?.length && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {(msg.stage2?.length > 0 || msg.stage2PendingModels?.length > 0) && (
                    <Stage2
                      rankings={msg.stage2 || []}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                      pendingModels={msg.stage2PendingModels || []}
                      isLoading={msg.loading?.stage2}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            multiple
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          
          <div className="input-wrapper">
            {/* Image previews */}
            {images.length > 0 && (
              <div className="image-previews">
                {images.map((img, index) => (
                  <div key={index} className="image-preview">
                    <img src={img} alt={`Preview ${index + 1}`} />
                    <button
                      type="button"
                      className="remove-image"
                      onClick={() => removeImage(index)}
                      title="Remove image"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="input-row">
              <button
                type="button"
                className="upload-button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading || images.length >= MAX_IMAGES}
                title={images.length >= MAX_IMAGES ? `Max ${MAX_IMAGES} images` : 'Attach images'}
              >
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
                </svg>
              </button>
              <textarea
                className="message-input"
                placeholder="Ask your question... (Shift+Enter for new line, Enter to send, paste images)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                disabled={isLoading}
                rows={3}
              />
              <button
                type="submit"
                className="send-button"
                disabled={(!input.trim() && images.length === 0) || isLoading}
              >
                Send
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Lightbox Modal */}
      {lightboxImage && (
        <div 
          className="lightbox-overlay" 
          onClick={() => setLightboxImage(null)}
        >
          <button 
            className="lightbox-close" 
            onClick={() => setLightboxImage(null)}
            title="Close"
          >
            ×
          </button>
          <img 
            src={lightboxImage} 
            alt="Enlarged view" 
            className="lightbox-image"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
