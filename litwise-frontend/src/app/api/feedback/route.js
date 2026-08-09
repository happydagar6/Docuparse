import { Resend } from 'resend';
import { NextResponse } from 'next/server';

const resend = new Resend(process.env.RESEND_API_KEY);

export async function POST(request) {
  try {
    // Check if Resend API key is configured
    if (!process.env.RESEND_API_KEY) {
      console.error('RESEND_API_KEY is not configured');
      return NextResponse.json(
        { error: 'Email service not configured' },
        { status: 500 }
      );
    }

    const { name, email, message, type = 'feedback' } = await request.json();

    // Validate required fields
    if (!name || !email || !message) {
      return NextResponse.json(
        { error: 'Name, email, and message are required' },
        { status: 400 }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    // Send email using Resend
    const { data, error } = await resend.emails.send({
      from: 'onboarding@resend.dev', // Use Resend's verified domain for development
      to: ['harshitdagar913@gmail.com'],
      subject: `DocuParse ${type === 'newsletter' ? 'Newsletter Subscription' : 'Feedback'} from ${name}`,
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <h2 style="color: #2563eb; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">
            ${type === 'newsletter' ? 'Newsletter Subscription' : 'New Feedback'} - DocuParse
          </h2>
          
          <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Name:</strong> ${name}</p>
            <p><strong>Email:</strong> ${email}</p>
            <p><strong>Type:</strong> ${type}</p>
          </div>
          
          ${type !== 'newsletter' ? `
          <div style="background-color: #ffffff; padding: 20px; border-left: 4px solid #2563eb; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #1f2937;">Message:</h3>
            <p style="line-height: 1.6; color: #374151;">${message}</p>
          </div>
          ` : ''}
          
          <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
            This ${type} was sent from the DocuParse application.
          </p>
        </div>
      `,
      replyTo: email
    });

    if (error) {
      console.error('Resend error:', error);
      
      // Handle specific error types
      if (error.statusCode === 403 && error.name === 'validation_error') {
        return NextResponse.json(
          { error: 'Email service configuration error. Please try again later.' },
          { status: 500 }
        );
      }
      
      return NextResponse.json(
        { error: 'Failed to send message. Please try again.' },
        { status: 500 }
      );
    }

    console.log('Email sent successfully:', data);
    return NextResponse.json({
      success: true,
      message: type === 'newsletter' 
        ? 'Successfully subscribed to newsletter!' 
        : 'Feedback sent successfully!'
    });

  } catch (error) {
    console.error('Feedback API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}