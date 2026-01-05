\<div class="flex flex-col h-full p-4 bg-slate-800"\>  
    \<div class="text-center mb-4"\>  
        \<h1 class="text-2xl font-bold text-slate-100"\>LUDI CHAT\</h1\>  
        \<p class="text-sm text-theme-gold"\>Query LudiDB with Natural Language\</p\>  
    \</div\>

    \<\!-- Chat Messages \--\>  
    \<div class="flex-grow overflow-y-auto pr-2 space-y-4"\>  
        @for (message of messages(); track $index) {  
            @if (message.role \=== 'user') {  
                \<div class="flex justify-end"\>  
                    \<div class="bg-theme-gold text-slate-900 rounded-lg p-3 max-w-lg"\>  
                        \<p class="font-semibold"\>{{ message.text }}\</p\>  
                    \</div\>  
                \</div\>  
            } @else if (message.role \=== 'model') {  
                \<div class="flex justify-start"\>  
                    \<div class="bg-slate-700 text-slate-200 rounded-lg p-3 max-w-lg"\>  
                        \<p\>{{ message.text }}\</p\>  
                    \</div\>  
                \</div\>  
            } @else if (message.role \=== 'system') {  
                 \<div class="flex justify-center"\>  
                    \<div class="bg-red-900/50 text-red-300 rounded-lg p-3 max-w-lg"\>  
                        \<p\>{{ message.text }}\</p\>  
                    \</div\>  
                \</div\>  
            }  
        }  
        @if(isLoading()) {  
            \<div class="flex justify-start"\>  
                \<div class="bg-slate-700 text-slate-200 rounded-lg p-3 max-w-lg"\>  
                    \<div class="flex items-center space-x-2"\>  
                        \<div class="w-2 h-2 bg-theme-gold rounded-full animate-bounce \[animation-delay:-0.3s\]"\>\</div\>  
                        \<div class="w-2 h-2 bg-theme-gold rounded-full animate-bounce \[animation-delay:-0.15s\]"\>\</div\>  
                        \<div class="w-2 h-2 bg-theme-gold rounded-full animate-bounce"\>\</div\>  
                    \</div\>  
                \</div\>  
            \</div\>  
        }  
    \</div\>

    \<\!-- Input Area \--\>  
    \<div class="mt-4 pt-4 border-t border-slate-700"\>  
      @if (isConfigured) {  
        \<form (ngSubmit)="sendMessage()" class="flex space-x-2"\>  
            \<input   
                type="text"   
                \[(ngModel)\]="userInput"  
                name="userInput"  
                placeholder="Ask about player props, matchups, or archetypes..."  
                class="flex-grow bg-slate-700 text-slate-200 placeholder-slate-400 p-3 rounded-lg border border-slate-600 focus:outline-none focus:ring-2 focus:ring-theme-gold"  
                \[disabled\]="isLoading()"\>  
            \<button   
                type="submit"  
                class="bg-theme-gold text-slate-900 font-bold px-6 py-3 rounded-lg hover:bg-amber-300 transition-colors disabled:bg-slate-600 disabled:cursor-not-allowed"  
                \[disabled\]="isLoading() || userInput().trim() \=== ''"\>  
                Send  
            \</button\>  
        \</form\>  
      } @else {  
        \<div class="text-center p-4 bg-yellow-900/50 border border-yellow-700 rounded-lg"\>  
          \<p class="font-bold text-yellow-300"\>Ludi Chat Disabled\</p\>  
          \<p class="text-sm text-yellow-400"\>Please configure your Gemini API key in \`src/services/gemini.service.ts\` to enable this feature.\</p\>  
        \</div\>  
      }  
    \</div\>  
\</div\>  
