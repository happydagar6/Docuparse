/**
 * Supabase Client for Browser (Client Components)
 * Uses singleton pattern for optimal performance
 */

import { createBrowserClient } from "@supabase/ssr"

export function createClient() {
    return createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    )
}

// Singleton instance for reuse
let supabaseInstance = null

export function getSupabaseClient() {
    if(!supabaseInstance){
        supabaseInstance = createClient(); // Create the client if it doesn't exist
    }
    return supabaseInstance;
};