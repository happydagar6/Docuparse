import { createClient } from "@/lib/supabase/client"; 
import { NextResponse } from "next/server";

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get("code");

    // If "next" is in param, use it as the redirect URL
    const next = searchParams.get("next") ?? "/";

    if(code){
        const supabase = createClient();
        const { error } = await supabase.auth.exchangeCodeForSession(code); // Exchange code for session
        if(!error){
            const forwardedHost = request.headers.get("x-forwarded-host");
            const isLocalEnv = process.env.NODE_ENV === "development";
            if (isLocalEnv){
                // we can be sure that there is no load balancer in between, so no need to watch for X-Forwarded-Host
                return NextResponse.redirect(`${origin}${next}`);
            } else if(forwardedHost){
                return NextResponse.redirect(`https://${forwardedHost}${next}`);
            } else {
                return NextResponse.redirect(`${origin}${next}`);
            }
        }
    }
    
    // return the user to an error page with instruction to try logging in again
    return NextResponse.redirect(`${origin}/auth/auth-code-error`);
}