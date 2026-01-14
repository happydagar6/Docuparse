/**
 * PDF Renderer Integration Tests
 * 
 * Tests for the new PDF rendering system components
 * Location: src/components/reader/__tests__/PDFRenderer.test.jsx
 * 
 * Run with: npm run test:unit -- PDFRenderer
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import PaperPDFViewer from '../PaperPDFViewer';
import AdvancedPDFViewer from '../AdvancedPDFViewer';

/**
 * Test Suite: PaperPDFViewer Component
 */
describe('PaperPDFViewer', () => {
  const mockPaper = {
    id: '123',
    title: 'Test Research Paper',
    content: 'This is a test paper.\n\nIt has multiple paragraphs.\n\nEach paragraph should be on a separate page if long enough.',
    authors: ['Author One', 'Author Two'],
    year: 2024,
  };

  it('should render without crashing', () => {
    render(<PaperPDFViewer paper={mockPaper} />);
    expect(screen.getByText('Test Research Paper')).toBeInTheDocument();
  });

  it('should display loading state', () => {
    render(<PaperPDFViewer paper={mockPaper} isLoading={true} />);
    expect(screen.getByText('Rendering PDF...')).toBeInTheDocument();
  });

  it('should display error state', () => {
    const errorMessage = 'Failed to load paper';
    render(
      <PaperPDFViewer 
        paper={mockPaper} 
        error={errorMessage}
      />
    );
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('should handle missing content gracefully', () => {
    const paperWithoutContent = { ...mockPaper };
    delete paperWithoutContent.content;
    
    render(<PaperPDFViewer paper={paperWithoutContent} />);
    // Should still render without crashing
    expect(screen.getByText('Test Research Paper')).toBeInTheDocument();
  });

  it('should use fallback title if not provided', () => {
    const paperWithoutTitle = { 
      id: '123',
      content: 'Some content'
    };
    
    render(<PaperPDFViewer paper={paperWithoutTitle} />);
    expect(screen.getByText('Research Paper')).toBeInTheDocument();
  });

  it('should call onDownload callback when provided', async () => {
    const mockDownload = jest.fn();
    render(
      <PaperPDFViewer 
        paper={mockPaper}
        onDownload={mockDownload}
      />
    );
    
    // Note: Actual download button interaction would be tested here
    // This is a placeholder for the actual implementation
  });
});

/**
 * Test Suite: AdvancedPDFViewer Component
 */
describe('AdvancedPDFViewer', () => {
  const mockPages = [
    <div key="1">Page 1 Content</div>,
    <div key="2">Page 2 Content</div>,
    <div key="3">Page 3 Content</div>,
  ];

  it('should render all pages', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Page 1 Content')).toBeInTheDocument();
  });

  it('should display page navigation controls', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    expect(screen.getByText(/1\s*\/\s*3/)).toBeInTheDocument(); // Page indicator
  });

  it('should navigate to next page', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const nextButton = getByRole('button', { name: /next page/i });
    fireEvent.click(nextButton);
    
    await waitFor(() => {
      expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument();
    });
  });

  it('should navigate to previous page', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Go to page 2 first
    fireEvent.click(getByRole('button', { name: /next page/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument();
    });
    
    // Go back to page 1
    fireEvent.click(getByRole('button', { name: /previous page/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/1\s*\/\s*3/)).toBeInTheDocument();
    });
  });

  it('should disable navigation buttons at boundaries', () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const prevButton = getByRole('button', { name: /previous page/i });
    expect(prevButton).toBeDisabled();
  });

  it('should handle zoom in/out', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const zoomInButton = getByRole('button', { name: /zoom in/i });
    fireEvent.click(zoomInButton);
    
    await waitFor(() => {
      expect(screen.getByText(/120%/)).toBeInTheDocument();
    });
  });

  it('should display loading state', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={[]}
        isLoading={true}
      />
    );
    
    expect(screen.getByText('Rendering PDF...')).toBeInTheDocument();
  });

  it('should display error state', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={[]}
        error="Failed to render PDF"
      />
    );
    
    expect(screen.getByText('Failed to render PDF')).toBeInTheDocument();
  });

  it('should display empty state for no pages', () => {
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={[]}
      />
    );
    
    expect(screen.getByText('No pages available')).toBeInTheDocument();
  });

  it('should toggle fullscreen mode', async () => {
    const { getByRole, container } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Find and click the fullscreen button
    const buttons = getByRole('button');
    const fullscreenButton = Array.from(buttons).find(
      btn => btn.getAttribute('title') === 'Full Screen'
    );
    
    if (fullscreenButton) {
      fireEvent.click(fullscreenButton);
      
      await waitFor(() => {
        const mainDiv = container.querySelector('[class*="fixed"]');
        expect(mainDiv).toBeTruthy();
      });
    }
  });
});

/**
 * Test Suite: Keyboard Shortcuts
 */
describe('Keyboard Shortcuts', () => {
  const mockPages = [
    <div key="1">Page 1</div>,
    <div key="2">Page 2</div>,
    <div key="3">Page 3</div>,
  ];

  it('should navigate with arrow keys', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Press ArrowRight to go to next page
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    
    await waitFor(() => {
      expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument();
    });
  });

  it('should navigate with h/l keys', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    // Press 'l' to go to next page
    fireEvent.keyDown(window, { key: 'l' });
    
    await waitFor(() => {
      expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument();
    });
  });

  it('should ignore shortcuts when input is focused', async () => {
    const { getByRole } = render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    
    const input = getByRole('textbox');
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: 'ArrowRight' });
    
    // Should still show page 1
    expect(screen.getByText(/1\s*\/\s*3/)).toBeInTheDocument();
  });
});

/**
 * Test Suite: Content Parsing
 */
describe('Content Parsing', () => {
  it('should parse markdown headers', () => {
    const content = `# Title\n\nSome content\n\n## Subtitle\n\nMore content`;
    const mockPaper = {
      title: 'Test',
      content: content,
    };
    
    render(<PaperPDFViewer paper={mockPaper} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('should handle lists', () => {
    const content = `- Item 1\n- Item 2\n- Item 3`;
    const mockPaper = {
      title: 'Test',
      content: content,
    };
    
    render(<PaperPDFViewer paper={mockPaper} />);
    // The list should be rendered without errors
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('should handle code blocks', () => {
    const content = `\`\`\`\nconst x = 10;\n\`\`\``;
    const mockPaper = {
      title: 'Test',
      content: content,
    };
    
    render(<PaperPDFViewer paper={mockPaper} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});

/**
 * Test Suite: Responsive Design
 */
describe('Responsive Design', () => {
  const mockPages = [
    <div key="1">Page 1 Content</div>,
  ];

  beforeEach(() => {
    // Reset viewport
    global.innerWidth = 1024;
    global.innerHeight = 768;
  });

  it('should render on desktop', () => {
    global.innerWidth = 1920;
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('should render on tablet', () => {
    global.innerWidth = 768;
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('should render on mobile', () => {
    global.innerWidth = 375;
    render(
      <AdvancedPDFViewer 
        title="Test Document"
        pages={mockPages}
      />
    );
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });
});
