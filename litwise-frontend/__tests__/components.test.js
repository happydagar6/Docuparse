/**
 * Jest Unit Tests for React Components
 * Tests individual component rendering and user interactions
 */

const React = require('react');
const { render, screen, fireEvent, waitFor } = require('@testing-library/react');
const { default: userEvent } = require('@testing-library/user-event');

// Mock LoginForm Component
const MockLoginForm = ({ onSubmit }) => {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email && password) {
      onSubmit({ email, password });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="email">Email</label>
      <input
        id="email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter email"
      />
      
      <label htmlFor="password">Password</label>
      <input
        id="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Enter password"
      />
      
      <button type="submit">Login</button>
    </form>
  );
};

// Mock ChatInterface Component
const MockChatInterface = ({ paperId }) => {
  const [messages, setMessages] = React.useState([]);
  const [input, setInput] = React.useState('');

  const handleSendMessage = () => {
    if (input.trim()) {
      setMessages([...messages, { text: input, sender: 'user' }]);
      setInput('');
    }
  };

  return (
    <div className="chat-interface">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className="message">
            {msg.text}
          </div>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type message..."
      />
      <button onClick={handleSendMessage}>Send</button>
    </div>
  );
};

// Mock CitationList Component
const MockCitationList = ({ citations, onRemove }) => {
  if (!citations || citations.length === 0) {
    return <div className="empty">No citations</div>;
  }

  return (
    <div className="citation-list">
      {citations.map((citation) => (
        <div key={citation.id} className="citation-item">
          <span>{citation.title}</span>
          <button onClick={() => onRemove(citation.id)}>Remove</button>
        </div>
      ))}
    </div>
  );
};

// Mock QuizConfigForm Component
const MockQuizConfigForm = ({ onSubmit }) => {
  const [difficulty, setDifficulty] = React.useState('medium');
  const [questionCount, setQuestionCount] = React.useState(5);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ difficulty, questionCount: parseInt(questionCount) });
  };

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="difficulty">Difficulty</label>
      <select
        id="difficulty"
        value={difficulty}
        onChange={(e) => setDifficulty(e.target.value)}
      >
        <option value="easy">Easy</option>
        <option value="medium">Medium</option>
        <option value="hard">Hard</option>
      </select>

      <label htmlFor="count">Questions</label>
      <input
        id="count"
        type="number"
        value={questionCount}
        onChange={(e) => setQuestionCount(e.target.value)}
        min="1"
        max="50"
      />

      <button type="submit">Create Quiz</button>
    </form>
  );
};

// Mock PaperReader Component
const MockPaperReader = ({ paperId, title }) => {
  const [isLoading, setIsLoading] = React.useState(false);
  const [content, setContent] = React.useState(null);

  React.useEffect(() => {
    if (paperId) {
      setIsLoading(true);
      setTimeout(() => {
        setContent(`Content for paper ${paperId}`);
        setIsLoading(false);
      }, 100);
    }
  }, [paperId]);

  if (isLoading) {
    return <div>Loading paper...</div>;
  }

  if (!content) {
    return <div>No paper loaded</div>;
  }

  return (
    <div className="paper-reader">
      <h2>{title}</h2>
      <div className="content">{content}</div>
    </div>
  );
};

// ============ TESTS ============

describe('LoginForm Component', () => {
  it('should render email and password inputs', () => {
    render(<MockLoginForm onSubmit={() => {}} />);
    
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('should update input values when user types', async () => {
    render(<MockLoginForm onSubmit={() => {}} />);
    
    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');

    expect(emailInput.value).toBe('test@example.com');
    expect(passwordInput.value).toBe('password123');
  });

  it('should submit form with email and password', async () => {
    const mockSubmit = jest.fn();
    render(<MockLoginForm onSubmit={mockSubmit} />);

    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByText('Login');

    await userEvent.type(emailInput, 'user@example.com');
    await userEvent.type(passwordInput, 'pass123');
    fireEvent.click(submitButton);

    expect(mockSubmit).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'pass123',
    });
  });

  it('should not submit if fields are empty', async () => {
    const mockSubmit = jest.fn();
    render(<MockLoginForm onSubmit={mockSubmit} />);

    const submitButton = screen.getByText('Login');
    fireEvent.click(submitButton);

    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('should render login button', () => {
    render(<MockLoginForm onSubmit={() => {}} />);
    expect(screen.getByText('Login')).toBeInTheDocument();
  });
});

describe('ChatInterface Component', () => {
  it('should render chat interface with input and send button', () => {
    render(<MockChatInterface paperId="123" />);
    
    expect(screen.getByPlaceholderText('Type message...')).toBeInTheDocument();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('should display message when sent', async () => {
    render(<MockChatInterface paperId="123" />);

    const input = screen.getByPlaceholderText('Type message...');
    const sendButton = screen.getByText('Send');

    await userEvent.type(input, 'Hello chatbot');
    fireEvent.click(sendButton);

    expect(screen.getByText('Hello chatbot')).toBeInTheDocument();
  });

  it('should clear input after sending message', async () => {
    render(<MockChatInterface paperId="123" />);

    const input = screen.getByPlaceholderText('Type message...');
    const sendButton = screen.getByText('Send');

    await userEvent.type(input, 'Test message');
    fireEvent.click(sendButton);

    expect(input.value).toBe('');
  });

  it('should not send empty message', async () => {
    render(<MockChatInterface paperId="123" />);

    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);

    // Check that no message divs exist in the messages container
    const messagesContainer = screen.getByText('Send').parentElement.querySelector('.messages');
    expect(messagesContainer.children.length).toBe(0);
  });

  it('should display multiple messages', async () => {
    render(<MockChatInterface paperId="123" />);

    const input = screen.getByPlaceholderText('Type message...');
    const sendButton = screen.getByText('Send');

    await userEvent.type(input, 'First message');
    fireEvent.click(sendButton);

    await userEvent.type(input, 'Second message');
    fireEvent.click(sendButton);

    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('Second message')).toBeInTheDocument();
  });
});

describe('CitationList Component', () => {
  it('should show empty message when no citations', () => {
    render(<MockCitationList citations={[]} onRemove={() => {}} />);
    expect(screen.getByText('No citations')).toBeInTheDocument();
  });

  it('should render citations', () => {
    const citations = [
      { id: 1, title: 'Paper 1' },
      { id: 2, title: 'Paper 2' },
    ];

    render(<MockCitationList citations={citations} onRemove={() => {}} />);

    expect(screen.getByText('Paper 1')).toBeInTheDocument();
    expect(screen.getByText('Paper 2')).toBeInTheDocument();
  });

  it('should call onRemove when remove button clicked', async () => {
    const mockRemove = jest.fn();
    const citations = [{ id: 1, title: 'Paper 1' }];

    render(<MockCitationList citations={citations} onRemove={mockRemove} />);

    const removeButtons = screen.getAllByText('Remove');
    fireEvent.click(removeButtons[0]);

    expect(mockRemove).toHaveBeenCalledWith(1);
  });

  it('should have remove button for each citation', () => {
    const citations = [
      { id: 1, title: 'Paper 1' },
      { id: 2, title: 'Paper 2' },
      { id: 3, title: 'Paper 3' },
    ];

    render(<MockCitationList citations={citations} onRemove={() => {}} />);

    const removeButtons = screen.getAllByText('Remove');
    expect(removeButtons).toHaveLength(3);
  });
});

describe('QuizConfigForm Component', () => {
  it('should render difficulty and question count inputs', () => {
    render(<MockQuizConfigForm onSubmit={() => {}} />);

    expect(screen.getByLabelText('Difficulty')).toBeInTheDocument();
    expect(screen.getByLabelText('Questions')).toBeInTheDocument();
  });

  it('should have default values', () => {
    render(<MockQuizConfigForm onSubmit={() => {}} />);

    const difficultySelect = screen.getByLabelText('Difficulty');
    const countInput = screen.getByLabelText('Questions');
    
    expect(difficultySelect.value).toBe('medium');
    expect(countInput.value).toBe('5');
  });

  it('should change difficulty level', async () => {
    render(<MockQuizConfigForm onSubmit={() => {}} />);

    const difficultySelect = screen.getByLabelText('Difficulty');
    await userEvent.selectOptions(difficultySelect, 'hard');

    expect(difficultySelect.value).toBe('hard');
  });

  it('should change question count', async () => {
    render(<MockQuizConfigForm onSubmit={() => {}} />);

    const countInput = screen.getByLabelText('Questions');
    await userEvent.clear(countInput);
    await userEvent.type(countInput, '10');

    expect(countInput.value).toBe('10');
  });

  it('should submit form with config values', async () => {
    const mockSubmit = jest.fn();
    render(<MockQuizConfigForm onSubmit={mockSubmit} />);

    const difficultySelect = screen.getByLabelText('Difficulty');
    const countInput = screen.getByLabelText('Questions');
    const submitButton = screen.getByText('Create Quiz');

    await userEvent.selectOptions(difficultySelect, 'hard');
    await userEvent.clear(countInput);
    await userEvent.type(countInput, '15');
    fireEvent.click(submitButton);

    expect(mockSubmit).toHaveBeenCalledWith({
      difficulty: 'hard',
      questionCount: 15,
    });
  });
});

describe('PaperReader Component', () => {
  it('should show loading state initially', () => {
    render(<MockPaperReader paperId="123" title="Test Paper" />);
    expect(screen.getByText('Loading paper...')).toBeInTheDocument();
  });

  it('should display paper content after loading', async () => {
    render(<MockPaperReader paperId="123" title="Test Paper" />);

    await waitFor(() => {
      expect(screen.getByText('Content for paper 123')).toBeInTheDocument();
    });
  });

  it('should display paper title', async () => {
    render(<MockPaperReader paperId="123" title="Machine Learning" />);

    await waitFor(() => {
      expect(screen.getByText('Machine Learning')).toBeInTheDocument();
    });
  });

  it('should show no paper message when paperId is empty', () => {
    render(<MockPaperReader paperId="" title="Test" />);
    expect(screen.getByText('No paper loaded')).toBeInTheDocument();
  });

  it('should reload content when paperId changes', async () => {
    const { rerender } = render(
      <MockPaperReader paperId="123" title="Paper 1" />
    );

    await waitFor(() => {
      expect(screen.getByText('Content for paper 123')).toBeInTheDocument();
    });

    rerender(<MockPaperReader paperId="456" title="Paper 2" />);

    await waitFor(() => {
      expect(screen.getByText('Content for paper 456')).toBeInTheDocument();
    });
  });
});
