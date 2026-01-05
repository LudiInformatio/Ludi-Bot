// \--- START OF FILE index.tsx \---

import '@angular/compiler';  
import { bootstrapApplication } from '@angular/platform-browser';  
import { AppComponent } from './src/app.component';  
import { provideZonelessChangeDetection } from '@angular/core';  
import { provideHttpClient } from '@angular/common/http';

bootstrapApplication(AppComponent, {  
  providers: \[  
    provideZonelessChangeDetection(),  
    provideHttpClient()  
  \]  
}).catch((err) \=\> console.error(err));

// AI Studio always uses an \`index.tsx\` file for all project types.  
// \--- END OF FILE index.tsx \---

// \--- START OF FILE metadata.json \---

{  
  "name": "NBA Model  Beta 1.0 (2025-2026)",  
  "description": "Professional NBA/WNBA betting model workflow implementing Scouting, Splits, Simulations (Pre/Post Yak), and AI-driven Spotlight Reports.",  
  "requestFramePermissions": \[\]  
}  
// \--- END OF FILE metadata.json \---

// \--- START OF FILE index.html \---

\<\!DOCTYPE html\>  
\<html lang="en"\>  
\<head\>  
  \<meta charset="UTF-g"\>  
  \<meta name="viewport" content="width=device-width, initial-scale=1.0"\>  
  \<title\>ProBet Analytics 2025\</title\>  
  \<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMiIgdmlld0JveD0iMCAwIDUxMiA1MTIiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHN0eWxlPi5jbHMtMXtmaWxsOiNmYmJmMjQ7fS5jbHMtMntmaWxsOiMwZjE3MmE7fTwvc3R5bGU+PC9kZWZzPjxjaXJjbGUgY2xhc3M9ImNscy0yIiBjeD0iMjU2IiBjeT0iMjU2IiByPSIyNDAiLz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0xOTcuNiwzOTIuOFYxMTkuMmgzOC40VjM1NC40aDk0LjR2MzguNEgxOTcuNloiLz48L3N2Zz4="\>  
  \<link rel="manifest" href="manifest.json"\>  
  \<meta name="theme-color" content="\#0f172a"\>  
  \<script src="https://cdn.tailwindcss.com"\>\</script\>  
  \<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"\>\</script\>  
  \<script\>  
    tailwind.config \= {  
      theme: {  
        extend: {  
          colors: {  
            slate: {  
              850: '\#1e293b',  
              900: '\#0f172a',  
              950: '\#020617',  
            },  
            amber: {  
              300: '\#fcd34d',  
              400: '\#fbbf24',  
              500: '\#f59e0b',  
              600: '\#d97706',  
            }  
          },  
          keyframes: {  
            'soft-pulse': {  
              '0%, 100%': { opacity: 0.2, transform: 'scale(1)' },  
              '50%': { opacity: 0.4, transform: 'scale(1.02)' },  
            }  
          },  
          animation: {  
            'soft-pulse': 'soft-pulse 3s ease-in-out infinite',  
          }  
        }  
      }  
    }  
  \</script\>  
\<style\>  
  body {  
    background-color: \#020617; /\* slate-950 \*/  
    /\* Blueprint Grid Background \*/  
    background-image:  
      linear-gradient(rgba(15, 116, 144, 0.08) 1px, transparent 1px),  
      linear-gradient(90deg, rgba(15, 116, 144, 0.08) 1px, transparent 1px);  
    background-size: 2rem 2rem;  
    background-position: center center;  
  }  
\</style\>  
\<script type="importmap"\>  
{  
  "imports": {  
    "rxjs": "https://esm.sh/rxjs@^7.8.2?conditions=es2015",  
    "rxjs/operators": "https://esm.sh/rxjs@^7.8.2/operators?conditions=es2015",  
    "rxjs/ajax": "https://esm.sh/rxjs@^7.8.2/ajax?conditions=es2015",  
    "rxjs/webSocket": "https://esm.sh/rxjs@^7.8.2/webSocket?conditions=es2015",  
    "rxjs/testing": "https://esm.sh/rxjs@^7.8.2/testing?conditions=es2015",  
    "rxjs/fetch": "https://esm.sh/rxjs@^7.8.2/fetch?conditions=es2015",  
    "@angular/core": "https://esm.sh/@angular/core@^21.0.6?external=rxjs",  
    "@google/genai": "https://esm.sh/@google/genai@^1.34.0?external=rxjs",  
    "@angular/compiler": "https://esm.sh/@angular/compiler@^21.0.6?external=rxjs",  
    "@angular/common": "https://esm.sh/@angular/common@^21.0.6?external=rxjs",  
    "@angular/platform-browser": "https://esm.sh/@angular/platform-browser@^21.0.6?external=rxjs",  
    "@angular/forms": "https://esm.sh/@angular/forms@^21.0.6?external=rxjs",  
    "@angular/common/http": "https://esm.sh/@angular/common@^21.0.6/http?external=rxjs"  
  }  
}  
\</script\>  
\</head\>  
\<body class="bg-slate-950 text-slate-100 font-sans antialiased h-screen overflow-hidden selection:bg-amber-500 selection:text-white"\>  
  \<app-root\>\</app-root\>  
\</body\>  
\</html\>  
// \--- END OF FILE index.html \---

// \--- START OF FILE manifest.json \---  
{  
  "name": "Ludi Informatio \- ProBet Analytics",  
  "short\_name": "Ludi",  
  "start\_url": ".",  
  "scope": ".",  
  "display\_override": \[  
    "standalone",  
    "minimal-ui"  
  \],  
  "display": "standalone",  
  "background\_color": "\#020617",  
  "theme\_color": "\#0f172a",  
  "description": "Professional NBA betting model workflow implementing Scouting, Splits, Simulations (Pre/Post Yak), and AI-driven Spotlight Reports.",  
  "icons": \[  
    {  
      "src": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMiIgdmlld0JveD0iMCAwIDUxMiA1MTIiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHN0eWxlPi5jbHMtMXtmaWxsOiNmYmJmMjQ7fS5jbHMtMntmaWxsOiMwZjE3MmE7fTwvc3R5bGU+PC9kZWZzPjxjaXJjbGUgY2xhc3M9ImNscy0yIiBjeD0iMjU2IiBjeT0iMjU2IiByPSIyNDAiLz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0xOTcuNiwzOTIuOFYxMTkuMmgzOC40VjM1NC40aDk0LjR2MzguNEgxOTcuNloiLz48L3N2Zz4=",  
      "sizes": "any",  
      "type": "image/svg+xml"  
    }  
  \]  
}  
// \--- END OF FILE manifest.json \---

// \--- START OF FILE src/app.component.ts \---  
import { Component, inject, effect, signal, computed } from '@angular/core';  
import { CommonModule } from '@angular/common';  
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';  
import { GameDashboardComponent } from './components/game-dashboard.component';  
import { ModelDataService } from './services/model-data.service';  
import { PlaybookComponent } from './components/playbook.component';  
import { ScenarioControlComponent } from './components/scenario-control.component';  
import { ScenarioStateService } from './services/scenario-state.service';  
import { NotificationContainerComponent } from './components/notification-container.component';  
import { HomeDashboardComponent } from './components/home-dashboard.component';  
import { LUDI\_LOGO\_BASE64 } from './assets/logo';  
import { AlchemistService } from './services/alchemist.service';  
import { AlchemistReportComponent } from './components/alchemist-report.component';  
import { LensStateService } from './services/lens-state.service';  
import { LensComponent } from './components/lens.component';

@Component({  
  selector: 'app-root',  
  standalone: true,  
  imports: \[CommonModule, GameDashboardComponent, PlaybookComponent, ScenarioControlComponent, NotificationContainerComponent, HomeDashboardComponent, AlchemistReportComponent, LensComponent\],  
  template: \`  
    \<div class="h-screen w-full grid lg:grid-cols-\[320px,1fr\] overflow-hidden"\>  
      \<\!-- Left Sidebar: Game List (Mobile: Sliding Panel, Desktop: Grid Column) \--\>  
      \<div   
        class="fixed lg:relative inset-y-0 left-0 z-40 w-80 lg:w-auto h-full flex-shrink-0 border-r border-sky-500/10 shadow-2xl shadow-black/50 bg-slate-950/80 backdrop-blur-md transition-transform duration-300 ease-in-out lg:translate-x-0"  
        \[class.-translate-x-full\]="\!isGameDashboardOpen()"  
        \[class.translate-x-0\]="isGameDashboardOpen()"\>  
        \<app-game-dashboard (close)="isGameDashboardOpen.set(false)"\>\</app-game-dashboard\>  
      \</div\>

      \<\!-- Main Content Area \--\>  
      \<div class="flex flex-col h-full overflow-hidden min-w-0"\>  
        \<\!-- Mobile Header (hidden on desktop) \--\>  
        \<header class="lg:hidden flex-shrink-0 flex items-center justify-between p-2 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md z-30"\>  
          \<button (click)="isGameDashboardOpen.set(true)" class="p-2 rounded-md hover:bg-slate-800"\>  
            \<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"\>\<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" /\>\</svg\>  
          \</button\>  
          @if(activeGame()) {  
            \<div class="text-xs font-bold text-center"\>  
              \<p\>{{activeGame()?.awayTeam}} @ {{activeGame()?.homeTeam}}\</p\>  
              \<p class="text-slate-400 font-mono text-\[10px\]"\>{{activeGame()?.time}}\</p\>  
            \</div\>  
          } @else {  
             \<div class="flex items-center gap-2"\>  
                \<img \[src\]="ludiLogo" alt="Ludi Logo" class="h-6 w-6"\>  
                \<span class="text-sm font-bold"\>Ludi Informatio\</span\>  
             \</div\>  
          }  
          \<\!-- CONTEXT-AWARE BUTTON \--\>  
          @if (activeGame()) {  
            \<button (click)="openScenarioControls()" class="p-2 rounded-md hover:bg-slate-800" title="Scenario Controls"\>  
               \<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor"\>\<path d="M17.293 3.293A8 8 0 002.707 17.293 8 8 0 0017.293 3.293zM9 5a1 1 0 012 0v2h2a1 1 0 110 2h-2v2a1 1 0 11-2 0v-2H7a1 1 0 110-2h2V5z" /\>\</svg\>  
            \</button\>  
          } @else {  
            \<button (click)="openGlobalLens()" class="p-2 rounded-md hover:bg-slate-800" title="Open AI Research Assistant"\>  
              \<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor"\>\<path d="M10 2a6 6 0 00-6 6c0 1.954 1.043 3.73 2.65 4.819A.5.5 0 016.5 13H6v1.5a.5.5 0 00.5.5h7a.5.5 0 00.5-.5V13h-.5a.5.5 0 01-.15-.981C14.957 11.73 16 9.954 16 8a6 6 0 00-6-6zm-3.5 15a.5.5 0 000 1h7a.5.5 0 000-1h-7z" /\>\</svg\>  
            \</button\>  
          }  
        \</header\>

        \<\!-- Main View (Playbook, etc) \--\>  
        \<main class="flex-1 grid grid-cols-1 lg:grid-cols-\[1fr,384px\] h-full overflow-hidden"\>  
          @if (dataService.isGameLoading()) {  
            \<div class="w-full h-full flex flex-col items-center justify-center bg-slate-950/50 lg:col-span-2"\>  
              \<div class="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"\>\</div\>  
              \<p class="text-amber-300 animate-pulse text-sm"\>{{ dataService.systemStatus() }}\</p\>  
            \</div\>  
          } @else if (activeGameId(); as id) {  
            @let game \= getGameById(id);  
            @if (game) {  
              \<\!-- Playbook takes first column \--\>  
              \<div class="h-full min-w-0 overflow-y-auto"\>  
                \<app-playbook \[game\]="game" (openScenarios)="openScenarioControls()"\>\</app-playbook\>  
              \</div\>  
                
              \<\!-- Right Sidebar: Scenario Controls (Static on Desktop only) \--\>  
              \<div class="h-full flex-shrink-0 z-10 hidden lg:block"\>  
                \<app-scenario-control\>\</app-scenario-control\>  
              \</div\>  
            }  
          } @else {  
            \<div class="lg:col-span-2 h-full overflow-y-auto"\>  
                \<app-home-dashboard\>\</app-home-dashboard\>  
            \</div\>  
          }  
        \</main\>  
      \</div\>  
        
      \<\!-- Right Sidebar (Mobile Sliding Panel) \--\>  
      \<div   
        class="lg:hidden fixed inset-y-0 right-0 z-40 w-96 max-w-\[90vw\] h-full bg-slate-900/90 backdrop-blur-md border-l border-sky-500/10 transition-transform duration-300 ease-in-out"  
        \[class.translate-x-full\]="\!isScenarioControlOpen()"  
        \[class.translate-x-0\]="isScenarioControlOpen()"\>  
        \<app-scenario-control (close)="isScenarioControlOpen.set(false)"\>\</app-scenario-control\>  
      \</div\>

      \<\!-- Overlays for mobile sidebars \--\>  
      @if (isGameDashboardOpen() || isScenarioControlOpen()) {  
        \<div (click)="isGameDashboardOpen.set(false); isScenarioControlOpen.set(false)" class="lg:hidden fixed inset-0 bg-black/60 z-30 backdrop-blur-sm"\>\</div\>  
      }

      \<\!-- Global Notification Toasts \--\>  
      \<app-notification-container\>\</app-notification-container\>

      \<\!-- Global Alchemist Report Modal \--\>  
      @if(alchemistService.showReport()) {  
        \<app-alchemist-report\>\</app-alchemist-report\>  
      }

      \<\!-- Global Lens Modal \--\>  
      @if(lensStateService.showLens()) {  
        \<app-lens\>\</app-lens\>  
      }  
    \</div\>  
  \`  
})  
export class AppComponent {  
  dataService \= inject(ModelDataService);  
  // ScenarioStateService is still injected to ensure it's created, but no longer manually controlled.  
  scenarioState \= inject(ScenarioStateService);   
  sanitizer: DomSanitizer \= inject(DomSanitizer);  
  alchemistService \= inject(AlchemistService);  
  lensStateService \= inject(LensStateService);

  isGameDashboardOpen \= signal(false);  
  isScenarioControlOpen \= signal(false);  
  ludiLogo: SafeResourceUrl;  
    
  activeGameId \= this.dataService.activeGameId;  
  activeGame \= computed(() \=\> {  
    const id \= this.activeGameId();  
    return id ? this.getGameById(id) : null;  
  });

  constructor() {  
    this.ludiLogo \= this.sanitizer.bypassSecurityTrustResourceUrl(LUDI\_LOGO\_BASE64);  
    this.dataService.initializeSeason();

    // Effect to handle mobile UI changes when a game is selected.  
    // The responsibility of initializing ScenarioState has been moved into that service itself.  
    effect(() \=\> {  
      if (this.dataService.activeGameId()) {  
        // Close sidebars on game selection for better mobile UX  
        this.isGameDashboardOpen.set(false);  
        this.isScenarioControlOpen.set(false);  
      }  
    });  
  }

  getGameById(id: string) {  
    return this.dataService.games().find(g \=\> g.id \=== id);  
  }

  openScenarioControls(): void {  
    this.isScenarioControlOpen.set(true);  
  }

  openGlobalLens(): void {  
    this.lensStateService.open(null);  
  }  
}  
// \--- END OF FILE src/app.component.ts \---

// \--- START OF FILE src/assets/logo.ts \---  
// Ludi Informatio Logo (Stylized L)  
// Base64 encoded SVG version of the Ludi Informatio logo.  
// Storing this as a constant prevents embedding a large string in multiple component files and ensures reliability.  
export const LUDI\_LOGO\_BASE64 \= 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMiIgdmlld0JveD0iMCAwIDUxMiA1MTIiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHN0eWxlPi5jbHMtMXtmaWxsOiNmYmJmMjQ7fS5jbHMtMntmaWxsOiMwZjE3MmE7fTwvc3R5bGU+PC9kZWZzPjxjaXJjbGUgY2xhc3M9ImNscy0yIiBjeD0iMjU2IiBjeT0iMjU2IiByPSIyNDAiLz48cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0xOTcuNiwzOTIuOFYxMTkuMmgzOC40VjM1NC40aDk0LjR2MzguNEgxOTcuNloiLz48L3N2Zz4=';  
// \--- END OF FILE src/assets/logo.ts \---

// \--- START OF FILE src/assets/ludi\_history\_db.json \---  
\[  
  {  
    "SEASON\_ID": "22025",  
    "TEAM\_ID": 1610612747,  
    "TEAM\_ABBREVIATION": "LAL",  
    "TEAM\_NAME": "Los Angeles Lakers",  
    "GAME\_ID": "0022500401",  
    "GAME\_DATE": "2025-12-18",  
    "MATCHUP": "LAL @ GSW",  
    "WL": "W",  
    "PTS": 118,  
    "PLUS\_MINUS": 5  
  },  
  {  
    "SEASON\_ID": "22025",  
    "TEAM\_ID": 1610612747,  
    "TEAM\_ABBREVIATION": "LAL",  
    "TEAM\_NAME": "Los Angeles Lakers",  
    "GAME\_ID": "0022500388",  
    "GAME\_DATE": "2025-12-15",  
    "MATCHUP": "LAL vs DEN",  
    "WL": "L",  
    "PTS": 102,  
    "PLUS\_MINUS": \-12  
  },  
  {  
    "SEASON\_ID": "22025",  
    "TEAM\_ID": 1610612738,  
    "TEAM\_ABBREVIATION": "BOS",  
    "TEAM\_NAME": "Boston Celtics",  
    "GAME\_ID": "0022500402",  
    "GAME\_DATE": "2025-12-18",  
    "MATCHUP": "BOS vs NYK",  
    "WL": "W",  
    "PTS": 125,  
    "PLUS\_MINUS": 12  
  },  
  {  
    "SEASON\_ID": "22025",  
    "TEAM\_ID": 1610612738,  
    "TEAM\_ABBREVIATION": "BOS",  
    "TEAM\_NAME": "Boston Celtics",  
    "GAME\_ID": "0022500395",  
    "GAME\_DATE": "2025-12-16",  
    "MATCHUP": "BOS @ PHI",  
    "WL": "W",  
    "PTS": 112,  
    "PLUS\_MINUS": 8  
  }  
\]  
// \--- END OF FILE src/assets/ludi\_history\_db.json \---

// \--- START OF FILE src/data/history-data.ts \---  
// Matches the structure of the "Census" Python script output (Player Logs)  
export interface GameLog {  
  SEASON\_ID: string;  
  PLAYER\_ID: number;  
  PLAYER\_NAME: string;  
  TEAM\_ID: number;  
  TEAM\_ABBREVIATION: string;  
  TEAM\_NAME: string;  
  GAME\_ID: string;  
  GAME\_DATE: string;  
  MATCHUP: string;  
  WL: string;  
  MIN: number;  
  FGM: number;  
  FGA: number;  
  FG\_PCT: number;  
  FG3M: number;  
  FG3A: number;  
  FG3\_PCT: number;  
  FTM: number;  
  FTA: number;  
  FT\_PCT: number;  
  OREB: number;  
  DREB: number;  
  REB: number;  
  AST: number;  
  STL: number;  
  BLK: number;  
  TOV: number;  
  PF: number;  
  PTS: number;  
  PLUS\_MINUS: number;  
  FANTASY\_PTS: number;  
  VIDEO\_AVAILABLE: number;  
}

export const HISTORY\_DATA: GameLog\[\] \= \[  
  // \--- USER SAMPLE DATA \---  
  {  
      "SEASON\_ID": "22025",  
      "PLAYER\_ID": 202699,  
      "PLAYER\_NAME": "Tobias Harris",  
      "TEAM\_ID": 1610612765,  
      "TEAM\_ABBREVIATION": "DET",  
      "TEAM\_NAME": "Detroit Pistons",  
      "GAME\_ID": "0022500007",  
      "GAME\_DATE": "2025-10-27",  
      "MATCHUP": "DET vs. CLE",  
      "WL": "L",  
      "MIN": 18,  
      "FGM": 2,  
      "FGA": 8,  
      "FG\_PCT": 0.25,  
      "FG3M": 2,  
      "FG3A": 5,  
      "FG3\_PCT": 0.4,  
      "FTM": 4,  
      "FTA": 4,  
      "FT\_PCT": 1.0,  
      "OREB": 0,  
      "DREB": 3,  
      "REB": 3,  
      "AST": 1,  
      "STL": 1,  
      "BLK": 0,  
      "TOV": 2,  
      "PF": 5,  
      "PTS": 10,  
      "PLUS\_MINUS": \-18,  
      "FANTASY\_PTS": 16.1,  
      "VIDEO\_AVAILABLE": 1  
  },  
  {  
      "SEASON\_ID": "22025",  
      "PLAYER\_ID": 1642845,  
      "PLAYER\_NAME": "VJ Edgecombe",  
      "TEAM\_ID": 1610612755,  
      "TEAM\_ABBREVIATION": "PHI",  
      "TEAM\_NAME": "Philadelphia 76ers",  
      "GAME\_ID": "0022500114",  
      "GAME\_DATE": "2025-10-27",  
      "MATCHUP": "PHI vs. ORL",  
      "WL": "W",  
      "MIN": 39,  
      "FGM": 10,  
      "FGA": 17,  
      "FG\_PCT": 0.588,  
      "FG3M": 2,  
      "FG3A": 4,  
      "FG3\_PCT": 0.5,  
      "FTM": 4,  
      "FTA": 4,  
      "FT\_PCT": 1.0,  
      "OREB": 2,  
      "DREB": 2,  
      "REB": 4,  
      "AST": 7,  
      "STL": 1,  
      "BLK": 1,  
      "TOV": 2,  
      "PF": 4,  
      "PTS": 26,  
      "PLUS\_MINUS": 13,  
      "FANTASY\_PTS": 45.3,  
      "VIDEO\_AVAILABLE": 1  
  },  
    
  // \--- EXPANDED MOCK DATASET FOR LAL/GSW \---  
  // Game 1: LAL vs GSW (2025-11-05) \- All players active  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 2544, "PLAYER\_NAME": "LeBron James", "TEAM\_ABBREVIATION": "LAL", "GAME\_ID": "0022500100", "GAME\_DATE": "2025-11-05", "PTS": 28, "REB": 8, "AST": 9, "MIN": 36, "FGM": 11, "FGA": 22, "FG3M": 2, "FG3A": 7, "FTM": 4, "FTA": 5, "OREB": 1, "DREB": 7, "STL": 1, "BLK": 1, "TOV": 4, "FANTASY\_PTS": 52.6, "TEAM\_ID": 1610612747, "TEAM\_NAME": "Los Angeles Lakers", "MATCHUP": "LAL vs GSW", "WL": "W", "FG\_PCT": 0.5, "FG3\_PCT": 0.286, "FT\_PCT": 0.8, "PF": 2, "PLUS\_MINUS": 10, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 203076, "PLAYER\_NAME": "Anthony Davis", "TEAM\_ABBREVIATION": "LAL", "GAME\_ID": "0022500100", "GAME\_DATE": "2025-11-05", "PTS": 24, "REB": 14, "AST": 3, "MIN": 35, "FGM": 9, "FGA": 18, "FG3M": 0, "FG3A": 1, "FTM": 6, "FTA": 7, "OREB": 4, "DREB": 10, "STL": 1, "BLK": 3, "TOV": 2, "FANTASY\_PTS": 54.5, "TEAM\_ID": 1610612747, "TEAM\_NAME": "Los Angeles Lakers", "MATCHUP": "LAL vs GSW", "WL": "W", "FG\_PCT": 0.5, "FG3\_PCT": 0, "FT\_PCT": 0.857, "PF": 3, "PLUS\_MINUS": 12, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 201939, "PLAYER\_NAME": "Stephen Curry", "TEAM\_ABBREVIATION": "GSW", "GAME\_ID": "0022500100", "GAME\_DATE": "2025-11-05", "PTS": 31, "REB": 5, "AST": 6, "MIN": 34, "FGM": 10, "FGA": 23, "FG3M": 5, "FG3A": 13, "FTM": 6, "FTA": 6, "OREB": 1, "DREB": 4, "STL": 2, "BLK": 0, "TOV": 3, "FANTASY\_PTS": 52.75, "TEAM\_ID": 1610612744, "TEAM\_NAME": "Golden State Warriors", "MATCHUP": "GSW @ LAL", "WL": "L", "FG\_PCT": 0.435, "FG3\_PCT": 0.385, "FT\_PCT": 1, "PF": 2, "PLUS\_MINUS": \-10, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 202691, "PLAYER\_NAME": "Klay Thompson", "TEAM\_ABBREVIATION": "GSW", "GAME\_ID": "0022500100", "GAME\_DATE": "2025-11-05", "PTS": 18, "REB": 4, "AST": 2, "MIN": 32, "FGM": 7, "FGA": 16, "FG3M": 4, "FG3A": 10, "FTM": 0, "FTA": 0, "OREB": 0, "DREB": 4, "STL": 1, "BLK": 0, "TOV": 1, "FANTASY\_PTS": 29, "TEAM\_ID": 1610612744, "TEAM\_NAME": "Golden State Warriors", "MATCHUP": "GSW @ LAL", "WL": "L", "FG\_PCT": 0.438, "FG3\_PCT": 0.4, "FT\_PCT": 0, "PF": 3, "PLUS\_MINUS": \-8, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 203952, "PLAYER\_NAME": "Andrew Wiggins", "TEAM\_ABBREVIATION": "GSW", "GAME\_ID": "0022500100", "GAME\_DATE": "2025-11-05", "PTS": 15, "REB": 6, "AST": 2, "MIN": 31, "FGM": 6, "FGA": 13, "FG3M": 1, "FG3A": 4, "FTM": 2, "FTA": 3, "OREB": 2, "DREB": 4, "STL": 1, "BLK": 1, "TOV": 2, "FANTASY\_PTS": 31.2, "TEAM\_ID": 1610612744, "TEAM\_NAME": "Golden State Warriors", "MATCHUP": "GSW @ LAL", "WL": "L", "FG\_PCT": 0.462, "FG3\_PCT": 0.25, "FT\_PCT": 0.667, "PF": 3, "PLUS\_MINUS": \-7, "VIDEO\_AVAILABLE": 1 },

  // Game 2: LAL vs DEN (2025-11-07) \- Anthony Davis OUT  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 2544, "PLAYER\_NAME": "LeBron James", "TEAM\_ABBREVIATION": "LAL", "GAME\_ID": "0022500115", "GAME\_DATE": "2025-11-07", "PTS": 32, "REB": 10, "AST": 11, "MIN": 38, "FGM": 12, "FGA": 24, "FG3M": 3, "FG3A": 8, "FTM": 5, "FTA": 5, "OREB": 2, "DREB": 8, "STL": 2, "BLK": 0, "TOV": 5, "FANTASY\_PTS": 62, "TEAM\_ID": 1610612747, "TEAM\_NAME": "Los Angeles Lakers", "MATCHUP": "LAL vs DEN", "WL": "L", "FG\_PCT": 0.5, "FG3\_PCT": 0.375, "FT\_PCT": 1, "PF": 1, "PLUS\_MINUS": \-5, "VIDEO\_AVAILABLE": 1 },  
  // Anthony Davis (203076) is missing from this game log  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 201939, "PLAYER\_NAME": "Stephen Curry", "TEAM\_ABBREVIATION": "GSW", "GAME\_ID": "0022500118", "GAME\_DATE": "2025-11-08", "PTS": 25, "REB": 6, "AST": 8, "MIN": 35, "FGM": 9, "FGA": 20, "FG3M": 3, "FG3A": 11, "FTM": 4, "FTA": 4, "OREB": 1, "DREB": 5, "STL": 1, "BLK": 1, "TOV": 2, "FANTASY\_PTS": 48.5, "TEAM\_ID": 1610612744, "TEAM\_NAME": "Golden State Warriors", "MATCHUP": "GSW vs HOU", "WL": "W", "FG\_PCT": 0.45, "FG3\_PCT": 0.273, "FT\_PCT": 1, "PF": 2, "PLUS\_MINUS": 15, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 202691, "PLAYER\_NAME": "Klay Thompson", "TEAM\_ABBREVIATION": "GSW", "GAME\_ID": "0022500118", "GAME\_DATE": "2025-11-08", "PTS": 22, "REB": 3, "AST": 1, "MIN": 30, "FGM": 8, "FGA": 15, "FG3M": 6, "FG3A": 11, "FTM": 0, "FTA": 0, "OREB": 0, "DREB": 3, "STL": 0, "BLK": 1, "TOV": 2, "FANTASY\_PTS": 28.75, "TEAM\_ID": 1610612744, "TEAM\_NAME": "Golden State Warriors", "MATCHUP": "GSW vs HOU", "WL": "W", "FG\_PCT": 0.533, "FG3\_PCT": 0.545, "FT\_PCT": 0, "PF": 4, "PLUS\_MINUS": 12, "VIDEO\_AVAILABLE": 1 },

  // Game 3: LAL vs GSW (2025-11-10) \- All players active again  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 2544, "PLAYER\_NAME": "LeBron James", "TEAM\_ABBREVIATION": "LAL", "GAME\_ID": "0022500130", "GAME\_DATE": "2025-11-10", "PTS": 25, "REB": 7, "AST": 7, "MIN": 35, "FGM": 10, "FGA": 20, "FG3M": 1, "FG3A": 5, "FTM": 4, "FTA": 6, "OREB": 1, "DREB": 6, "STL": 0, "BLK": 1, "TOV": 3, "FANTASY\_PTS": 43.25, "TEAM\_ID": 1610612747, "TEAM\_NAME": "Los Angeles Lakers", "MATCHUP": "LAL @ GSW", "WL": "L", "FG\_PCT": 0.5, "FG3\_PCT": 0.2, "FT\_PCT": 0.667, "PF": 2, "PLUS\_MINUS": \-8, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 203076, "PLAYER\_NAME": "Anthony Davis", "TEAM\_ABBREVIATION": "LAL", "GAME\_ID": "0022500130", "GAME\_DATE": "2025-11-10", "PTS": 27, "REB": 15, "AST": 2, "MIN": 36, "FGM": 11, "FGA": 19, "FG3M": 1, "FG3A": 2, "FTM": 4, "FTA": 5, "OREB": 5, "DREB": 10, "STL": 2, "BLK": 2, "TOV": 1, "FANTASY\_PTS": 58.25, "TEAM\_ID": 1610612747, "TEAM\_NAME": "Los Angeles Lakers", "MATCHUP": "LAL @ GSW", "WL": "L", "FG\_PCT": 0.579, "FG3\_PCT": 0.5, "FT\_PCT": 0.8, "PF": 3, "PLUS\_MINUS": \-6, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 201939, "PLAYER\_NAME": "Stephen Curry", "TEAM\_ABBREVIATION": "GSW", "GAME\_ID": "0022500130", "GAME\_DATE": "2025-11-10", "PTS": 35, "REB": 4, "AST": 5, "MIN": 36, "FGM": 12, "FGA": 25, "FG3M": 7, "FG3A": 15, "FTM": 4, "FTA": 4, "OREB": 0, "DREB": 4, "STL": 1, "BLK": 0, "TOV": 2, "FANTASY\_PTS": 52.5, "TEAM\_ID": 1610612744, "TEAM\_NAME": "Golden State Warriors", "MATCHUP": "GSW vs LAL", "WL": "W", "FG\_PCT": 0.48, "FG3\_PCT": 0.467, "FT\_PCT": 1, "PF": 1, "PLUS\_MINUS": 8, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 202691, "PLAYER\_NAME": "Klay Thompson", "TEAM\_ABBREVIATION": "GSW", "GAME\_ID": "0022500130", "GAME\_DATE": "2025-11-10", "PTS": 15, "REB": 5, "AST": 3, "MIN": 31, "FGM": 6, "FGA": 14, "FG3M": 3, "FG3A": 8, "FTM": 0, "FTA": 0, "OREB": 1, "DREB": 4, "STL": 1, "BLK": 1, "TOV": 1, "FANTASY\_PTS": 30.75, "TEAM\_ID": 1610612744, "TEAM\_NAME": "Golden State Warriors", "MATCHUP": "GSW vs LAL", "WL": "W", "FG\_PCT": 0.429, "FG3\_PCT": 0.375, "FT\_PCT": 0, "PF": 2, "PLUS\_MINUS": 10, "VIDEO\_AVAILABLE": 1 },

  // \--- NEWLY ADDED DATA FOR MISSING PLAYERS \---  
  // Game 4: DET vs MIA (2025-11-12)  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 1630595, "PLAYER\_NAME": "Cade Cunningham", "TEAM\_ABBREVIATION": "DET", "GAME\_ID": "0022500145", "GAME\_DATE": "2025-11-12", "PTS": 22, "REB": 6, "AST": 8, "MIN": 34, "FGM": 8, "FGA": 19, "FG3M": 2, "FG3A": 7, "FTM": 4, "FTA": 4, "OREB": 1, "DREB": 5, "STL": 1, "BLK": 0, "TOV": 4, "FANTASY\_PTS": 41.2, "TEAM\_ID": 1610612765, "TEAM\_NAME": "Detroit Pistons", "MATCHUP": "DET vs MIA", "WL": "L", "FG\_PCT": 0.421, "FG3\_PCT": 0.286, "FT\_PCT": 1.0, "PF": 3, "PLUS\_MINUS": \-9, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 1631093, "PLAYER\_NAME": "Jaden Ivey", "TEAM\_ABBREVIATION": "DET", "GAME\_ID": "0022500145", "GAME\_DATE": "2025-11-12", "PTS": 18, "REB": 4, "AST": 4, "MIN": 30, "FGM": 7, "FGA": 15, "FG3M": 2, "FG3A": 6, "FTM": 2, "FTA": 3, "OREB": 0, "DREB": 4, "STL": 2, "BLK": 0, "TOV": 3, "FANTASY\_PTS": 31.8, "TEAM\_ID": 1610612765, "TEAM\_NAME": "Detroit Pistons", "MATCHUP": "DET vs MIA", "WL": "L", "FG\_PCT": 0.467, "FG3\_PCT": 0.333, "FT\_PCT": 0.667, "PF": 2, "PLUS\_MINUS": \-5, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 1630589, "PLAYER\_NAME": "Ausar Thompson", "TEAM\_ABBREVIATION": "DET", "GAME\_ID": "0022500145", "GAME\_DATE": "2025-11-12", "PTS": 12, "REB": 8, "AST": 3, "MIN": 32, "FGM": 5, "FGA": 11, "FG3M": 1, "FG3A": 3, "FTM": 1, "FTA": 2, "OREB": 3, "DREB": 5, "STL": 2, "BLK": 2, "TOV": 2, "FANTASY\_PTS": 36.6, "TEAM\_ID": 1610612765, "TEAM\_NAME": "Detroit Pistons", "MATCHUP": "DET vs MIA", "WL": "L", "FG\_PCT": 0.455, "FG3\_PCT": 0.333, "FT\_PCT": 0.5, "PF": 4, "PLUS\_MINUS": \-11, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 1631206, "PLAYER\_NAME": "Jaime Jaquez Jr.", "TEAM\_ABBREVIATION": "MIA", "GAME\_ID": "0022500145", "GAME\_DATE": "2025-11-12", "PTS": 19, "REB": 7, "AST": 3, "MIN": 33, "FGM": 7, "FGA": 14, "FG3M": 1, "FG3A": 4, "FTM": 4, "FTA": 5, "OREB": 2, "DREB": 5, "STL": 1, "BLK": 0, "TOV": 1, "FANTASY\_PTS": 35.9, "TEAM\_ID": 1610612748, "TEAM\_NAME": "Miami Heat", "MATCHUP": "MIA @ DET", "WL": "W", "FG\_PCT": 0.5, "FG3\_PCT": 0.25, "FT\_PCT": 0.8, "PF": 2, "PLUS\_MINUS": 9, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 203932, "PLAYER\_NAME": "Duncan Robinson", "TEAM\_ABBREVIATION": "MIA", "GAME\_ID": "0022500145", "GAME\_DATE": "2025-11-12", "PTS": 15, "REB": 3, "AST": 2, "MIN": 28, "FGM": 5, "FGA": 10, "FG3M": 5, "FG3A": 10, "FTM": 0, "FTA": 0, "OREB": 0, "DREB": 3, "STL": 1, "BLK": 0, "TOV": 1, "FANTASY\_PTS": 25.6, "TEAM\_ID": 1610612748, "TEAM\_NAME": "Miami Heat", "MATCHUP": "MIA @ DET", "WL": "W", "FG\_PCT": 0.5, "FG3\_PCT": 0.5, "FT\_PCT": 1.0, "PF": 3, "PLUS\_MINUS": 12, "VIDEO\_AVAILABLE": 1 },

  // Game 5: LAC vs SAC (2025-11-15)  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 202331, "PLAYER\_NAME": "Norman Powell", "TEAM\_ABBREVIATION": "LAC", "GAME\_ID": "0022500158", "GAME\_DATE": "2025-11-15", "PTS": 17, "REB": 3, "AST": 1, "MIN": 25, "FGM": 6, "FGA": 12, "FG3M": 3, "FG3A": 7, "FTM": 2, "FTA": 2, "OREB": 1, "DREB": 2, "STL": 1, "BLK": 0, "TOV": 1, "FANTASY\_PTS": 24.1, "TEAM\_ID": 1610612746, "TEAM\_NAME": "Los Angeles Clippers", "MATCHUP": "LAC @ SAC", "WL": "W", "FG\_PCT": 0.5, "FG3\_PCT": 0.429, "FT\_PCT": 1.0, "PF": 2, "PLUS\_MINUS": 6, "VIDEO\_AVAILABLE": 1 },  
  { "SEASON\_ID": "22025", "PLAYER\_ID": 1630559, "PLAYER\_NAME": "Davion Mitchell", "TEAM\_ABBREVIATION": "SAC", "GAME\_ID": "0022500158", "GAME\_DATE": "2025-11-15", "PTS": 8, "REB": 2, "AST": 4, "MIN": 22, "FGM": 3, "FGA": 8, "FG3M": 1, "FG3A": 4, "FTM": 1, "FTA": 1, "OREB": 0, "DREB": 2, "STL": 2, "BLK": 0, "TOV": 2, "FANTASY\_PTS": 18.4, "TEAM\_ID": 1610612758, "TEAM\_NAME": "Sacramento Kings", "MATCHUP": "SAC vs LAC", "WL": "L", "FG\_PCT": 0.375, "FG3\_PCT": 0.25, "FT\_PCT": 1.0, "PF": 3, "PLUS\_MINUS": \-8, "VIDEO\_AVAILABLE": 1 }  
\];  
// \--- END OF FILE src/data/history-data.ts \---

// \--- START OF FILE src/components/alchemist-report.component.ts \---  
import { Component, computed, signal, inject } from '@angular/core';  
import { CommonModule, DatePipe } from '@angular/common';  
import { AlchemistService, AlchemistBet, PlayerPropBet, GameBet } from '../services/alchemist.service';

@Component({  
  selector: 'app-alchemist-report',  
  standalone: true,  
  imports: \[CommonModule, DatePipe\],  
  template: \`  
    \<div class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 animate-in fade-in-25" (click)="alchemistService.closeReport()"\>\</div\>  
    \<div class="report-modal fixed inset-y-4 right-4 w-\[520px\] max-w-\[95vw\] bg-slate-900 rounded-lg border border-slate-700 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right-8 duration-300"\>  
        
      \<\!-- Header \--\>  
      \<div class="p-4 border-b border-slate-800 flex justify-between items-center flex-shrink-0"\>  
        \<div\>  
          \<h2 class="text-lg font-bold text-white flex items-center gap-2"\>  
            \<span class="text-xl"\>📰\</span\> Ludi Elite Briefing  
          \</h2\>  
          \<p class="text-xs text-slate-500 font-mono"\>Generated: {{ generatedAt() | date:'shortTime' }}\</p\>  
        \</div\>  
        \<button (click)="alchemistService.closeReport()" class="text-slate-500 hover:text-white transition-colors text-2xl leading-none"\>\&times;\</button\>  
      \</div\>

      \<\!-- Content \--\>  
      \<div class="flex-1 overflow-y-auto p-4 space-y-6"\>  
        @if (alchemistService.isGenerating() && report().length \=== 0\) {  
          \<div class="h-full flex flex-col items-center justify-center text-center text-slate-500 p-8"\>  
              \<div class="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"\>\</div\>  
              \<p class="text-amber-300 animate-pulse text-sm"\>Generating Elite Briefing...\</p\>  
              \<p class="text-xs text-slate-600 mt-2"\>Analyzing all games on the slate for high-EV edges.\</p\>  
          \</div\>  
        } @else if (\!alchemistService.isGenerating() && report().length \=== 0\) {  
          \<div class="h-full flex items-center justify-center text-center text-slate-500 p-8"\>  
            \<div class="flex flex-col items-center"\>  
              \<svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"\>\<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /\>\</svg\>  
              \<p class="font-medium"\>Market is Efficient\</p\>  
              \<p class="text-xs"\>No high-value edges detected for this refresh.\</p\>  
            \</div\>  
          \</div\>  
        } @else {  
          \<\!-- NEW: Top Game Lines Section \--\>  
          @if (categorizedBets().gameBets.length \> 0\) {  
            \<div\>  
              \<h3 class="font-bold text-amber-400 mb-2 text-sm uppercase tracking-wider flex items-center gap-2"\>  
                📈 Top Game Lines  
              \</h3\>  
              \<div class="space-y-3"\>  
                @for(bet of categorizedBets().gameBets; track $index) {  
                  \<div class="bg-slate-800/50 p-3 rounded-lg border"  
                       \[class.border-amber-500/30\]="bet.tier \=== 'gold'"  
                       \[class.border-slate-700/50\]="bet.tier \=== 'silver'"\>  
                    \<ng-container \*ngTemplateOutlet="gameBetCard; context: { bet: bet }"\>\</ng-container\>  
                  \</div\>  
                }  
              \</div\>  
            \</div\>  
          }

          \<\!-- Player Props Section \--\>  
          @if (categorizedBets().playerPropBets.length \> 0\) {  
            \<div\>  
              \<h3 class="font-bold text-slate-300 mb-2 text-sm uppercase tracking-wider flex items-center gap-2 pt-4 border-t border-slate-800"\>  
                👤 Top Player Props  
              \</h3\>  
               \<\!-- Diamond Plays \--\>  
              @if (categorizedBets().diamondPlays.length \> 0\) {  
                \<div class="mt-2 space-y-3"\>  
                  @for(bet of categorizedBets().diamondPlays; track $index) {  
                    \<div class="bg-slate-800/50 p-3 rounded-lg border border-amber-500/30"\>  
                      \<ng-container \*ngTemplateOutlet="playerPropCard; context: { bet: bet, tier: 'diamond' }"\>\</ng-container\>  
                    \</div\>  
                  }  
                \</div\>  
              }

              \<\!-- Gold Plays \--\>  
              @if (categorizedBets().goldPlays.length \> 0\) {  
                \<div class="mt-3 space-y-3"\>  
                  @for(bet of categorizedBets().goldPlays; track $index) {  
                    \<div class="bg-slate-800/50 p-3 rounded-lg border border-slate-700"\>  
                      \<ng-container \*ngTemplateOutlet="playerPropCard; context: { bet: bet, tier: 'gold' }"\>\</ng-container\>  
                    \</div\>  
                  }  
                \</div\>  
              }  
              \<\!-- Silver Plays \--\>  
              @if (categorizedBets().silverPlays.length \> 0\) {  
                \<div class="mt-3 space-y-3"\>  
                  @for(bet of categorizedBets().silverPlays; track $index) {  
                    \<div class="bg-slate-800/50 p-3 rounded-lg border border-slate-800"\>  
                      \<ng-container \*ngTemplateOutlet="playerPropCard; context: { bet: bet, tier: 'silver' }"\>\</ng-container\>  
                    \</div\>  
                  }  
                \</div\>  
              }  
            \</div\>  
          }  
        }  
      \</div\>  
    \</div\>

    \<\!-- Player Prop Bet Card Template \--\>  
    \<ng-template \#playerPropCard let-bet="bet" let-tier="tier"\>  
      \<div class="flex justify-between items-start"\>  
        \<div\>  
          \<p class="font-bold text-white"\>{{ bet.name }} ({{ bet.team }})\</p\>  
          \<p class="text-sm" \[class.text-emerald-400\]="bet.betOn \=== 'OVER'" \[class.text-red-400\]="bet.betOn \=== 'UNDER'"\>  
            {{ bet.betOn }} {{ bet.line }} {{ bet.stat }}  
          \</p\>  
        \</div\>  
        \<span class="text-xs bg-slate-900 px-2 py-0.5 rounded border font-mono"  
              \[class.text-amber-300\]="tier \=== 'diamond'"  
              \[class.border-amber-700\]="tier \=== 'diamond'"  
              \[class.text-yellow-300\]="tier \=== 'gold'"  
              \[class.border-yellow-700\]="tier \=== 'gold'"  
              \[class.text-slate-300\]="tier \=== 'silver'"  
              \[class.border-slate-600\]="tier \=== 'silver'"\>{{ bet.units | number:'1.2-2' }}u\</span\>  
      \</div\>  
      \<div class="text-xs text-slate-400 mt-2 flex items-center gap-2 font-mono bg-slate-900/50 p-2 rounded border border-slate-800"\>  
        \<span\>PROJ: {{ bet.proj }}\</span\>  
        \<div class="h-4 border-l border-slate-700"\>\</div\>  
        \<span\>EV: \+{{ bet.ev }}%\</span\>  
        \<div class="relative group ml-auto"\>  
          \<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-500 cursor-pointer hover:text-white" viewBox="0 0 20 20" fill="currentColor"\>\<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" /\>\</svg\>  
          \<div class="absolute bottom-full left-1/2 \-translate-x-1/2 mb-2 w-72 bg-slate-950 border border-slate-700 rounded-md shadow-lg p-2 text-xs text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10"\>  
            \<div class="font-bold text-amber-400 border-b border-slate-700 pb-1 mb-1"\>Projection Breakdown\</div\>  
            \<div class="font-mono text-\[10px\] space-y-1"\>  
              \<div class="flex justify-between"\>\<span\>L20 Baseline:\</span\> \<span\>{{ bet.breakdown.baseline | number:'1.1-1' }}\</span\>\</div\>  
              \<div class="text-slate-500 italic whitespace-pre-line"\>Notes: {{ bet.breakdown.calibrationNotes || 'None' }}\</div\>  
              \<div class="flex justify-between border-t border-slate-700 pt-1 font-bold text-white"\>\<span\>Final Proj:\</span\> \<span\>{{ bet.proj | number:'1.1-1' }}\</span\>\</div\>  
            \</div\>  
            \<div class="absolute bottom-0 left-1/2 \-translate-x-1/2 translate-y-1/2 rotate-45 w-2 h-2 bg-slate-700"\>\</div\>  
          \</div\>  
        \</div\>  
      \</div\>  
      @if (bet.note) {  
        \<p class="text-\[10px\] text-amber-300/80 mt-2 border-t border-slate-700/50 pt-2 italic"\>  
          📝 {{ bet.note }}  
        \</p\>  
      }  
    \</ng-template\>

    \<\!-- Game Bet Card Template \--\>  
    \<ng-template \#gameBetCard let-bet="bet"\>  
       \<div class="flex justify-between items-start"\>  
        \<div\>  
          \<p class="font-bold text-white"\>{{ bet.awayTeam }} @ {{ bet.homeTeam }}\</p\>  
          \<p class="text-sm font-bold" \[class.text-emerald-400\]="bet.pick.includes('OVER') || \!bet.pick.includes('UNDER')" \[class.text-red-400\]="bet.pick.includes('UNDER')"\>  
            {{ bet.pick }}  
          \</p\>  
        \</div\>  
        \<span class="text-xs bg-slate-900 px-2 py-0.5 rounded border font-mono"  
              \[class.text-amber-300\]="bet.tier \=== 'gold'"  
              \[class.border-amber-700\]="bet.tier \=== 'gold'"  
              \[class.text-slate-300\]="bet.tier \=== 'silver'"  
              \[class.border-slate-600\]="bet.tier \=== 'silver'"\>{{ bet.units | number:'1.2-2' }}u\</span\>  
      \</div\>  
       \<div class="text-xs text-slate-400 mt-2 font-mono bg-slate-900/50 p-2 rounded border border-slate-800"\>  
        {{ bet.note }}  
      \</div\>  
    \</ng-template\>  
  \`,  
  styles: \[\`  
    :host { display: block; }  
    .report-modal { contain: content; }  
  \`\]  
})  
export class AlchemistReportComponent {  
  alchemistService \= inject(AlchemistService);  
  report \= this.alchemistService.report;  
    
  generatedAt \= signal(new Date());

  // NEW: Consolidated computed signal for performance and clarity.  
  categorizedBets \= computed(() \=\> {  
    const reportData \= this.report();  
    const playerPropBets \= reportData.filter((b): b is PlayerPropBet \=\> b.type \=== 'player');  
    const gameBets \= reportData.filter((b): b is GameBet \=\> b.type \!== 'player');  
      
    // Sort game bets to bring gold tier to the top  
    gameBets.sort((a, b) \=\> {  
      if (a.tier \=== 'gold' && b.tier \!== 'gold') return \-1;  
      if (a.tier \!== 'gold' && b.tier \=== 'gold') return 1;  
      return 0; // maintain original sort for same-tier bets  
    });

    return {  
      gameBets: gameBets,  
      playerPropBets: playerPropBets,  
      diamondPlays: playerPropBets.filter(p \=\> p.ev \>= 10.0),  
      goldPlays: playerPropBets.filter(p \=\> p.ev \>= 5.0 && p.ev \< 10.0),  
      silverPlays: playerPropBets.filter(p \=\> p.ev \< 5.0)  
    };  
  });  
}  
// \--- END OF FILE src/components/alchemist-report.component.ts \---

// \--- START OF FILE src/components/analytics-panel.component.ts \---  
import { Component, computed, effect, inject, input } from '@angular/core';  
import { CommonModule, DecimalPipe } from '@angular/common';  
import { AnalyticsService, TeamProfile, TeamSplits } from '../services/analytics.service';  
import { Player } from '../services/model-data.service';

@Component({  
  selector: 'app-analytics-panel',  
  standalone: true,  
  imports: \[CommonModule, DecimalPipe\],  
  template: \`  
    \<div class="bg-slate-800/40 p-4 rounded-lg border border-slate-700/50 h-full"\>  
      \<h4 class="font-bold text-slate-300 text-sm mb-3"\>Team Analytics\</h4\>  
        
      @if (profiles(); as prof) {  
        \<div class="space-y-4 text-xs"\>  
          \<\!-- Profiles \--\>  
          \<div class="grid grid-cols-2 gap-3"\>  
            \<div class="bg-slate-900/50 p-3 rounded"\>  
              \<p class="font-bold text-emerald-400/80 mb-1"\>Offensive DNA\</p\>  
              \<div class="space-y-1 font-mono text-slate-300/80"\>  
                \<p\>Pace: {{ prof.offensive.pace }}\</p\>  
                \<p\>3PT Rate: {{ prof.offensive.threePointRate | number: '1.0-1' }}%\</p\>  
                \<p\>FT Rate: {{ prof.offensive.freeThrowRate | number: '1.0-1' }}%\</p\>  
              \</div\>  
            \</div\>  
            \<div class="bg-slate-900/50 p-3 rounded"\>  
              \<p class="font-bold text-red-400/80 mb-1"\>Defensive DNA\</p\>  
              \<div class="space-y-1 font-mono text-slate-300/80"\>  
                \<p\>Pace: {{ prof.defensive.pace }}\</p\>  
                \<p\>3PT Allowed: {{ prof.defensive.threePointRate | number: '1.0-1' }}%\</p\>  
                \<p\>Opp FT Rate: {{ prof.defensive.freeThrowRate | number: '1.0-1' }}%\</p\>  
              \</div\>  
            \</div\>  
          \</div\>

          \<\!-- Shot Profile \--\>  
          \<div\>  
            \<p class="text-\[11px\] font-semibold text-slate-400 mb-1 uppercase tracking-wider"\>Shot Profile (Offense)\</p\>  
            \<div class="w-full bg-slate-900/50 rounded-full h-4 flex overflow-hidden border border-slate-700"\>  
              \<div class="bg-sky-500 h-full flex items-center justify-center text-\[10px\] font-bold" \[style.width.%\]="prof.offensive.shotProfile.rimPct" title="At Rim"\>{{ prof.offensive.shotProfile.rimPct | number:'1.0-0' }}%\</div\>  
              \<div class="bg-amber-500 h-full flex items-center justify-center text-\[10px\] font-bold" \[style.width.%\]="prof.offensive.shotProfile.midPct" title="Mid-Range"\>{{ prof.offensive.shotProfile.midPct | number:'1.0-0' }}%\</div\>  
              \<div class="bg-indigo-500 h-full flex items-center justify-center text-\[10px\] font-bold" \[style.width.%\]="prof.offensive.shotProfile.threePct" title="3-Pointer"\>{{ prof.offensive.shotProfile.threePct | number:'1.0-0' }}%\</div\>  
            \</div\>  
          \</div\>  
            
          \<\!-- Opponent Scheme \--\>  
          \<div class="bg-slate-900/50 p-2 rounded text-center"\>  
             \<p class="text-\[10px\] text-slate-400 uppercase font-bold tracking-wider"\>vs Opponent Scheme\</p\>  
             \<p class="font-mono text-indigo-300"\>{{ opponentDefStyle() }}\</p\>  
          \</div\>

          \<\!-- Splits \--\>  
          @if (splits(); as s) {  
            \<div class="bg-slate-900/50 p-3 rounded"\>  
                \<div class="grid grid-cols-2 gap-3 text-center"\>  
                    \<div\>  
                        \<p class="text-slate-400 text-\[11px\] uppercase tracking-wide font-semibold"\>Home\</p\>  
                        \<p class="font-mono font-bold text-lg text-white"\>{{ s.homeRecord }}\</p\>  
                        \<p class="font-mono text-\[10px\] text-slate-300"\>{{s.avgPtsForHome}} / {{s.avgPtsAgainstHome}}\</p\>  
                    \</div\>  
                    \<div\>  
                        \<p class="text-slate-400 text-\[11px\] uppercase tracking-wide font-semibold"\>Away\</p\>  
                        \<p class="font-mono font-bold text-lg text-white"\>{{ s.awayRecord }}\</p\>  
                        \<p class="font-mono text-\[10px\] text-slate-300"\>{{s.avgPtsForAway}} / {{s.avgPtsAgainstAway}}\</p\>  
                    \</div\>  
                \</div\>  
            \</div\>  
          }  
        \</div\>  
      } @else {  
        \<p class="text-center text-slate-500 text-sm"\>Loading analytics...\</p\>  
      }  
    \</div\>  
  \`,  
  styles: \[':host { display: block; contain: layout paint; }'\]  
})  
export class AnalyticsPanelComponent {  
  analyticsService \= inject(AnalyticsService);

  teamAbbr \= input.required\<string\>();  
  roster \= input.required\<Player\[\]\>();  
  opponentDefStyle \= input.required\<string\>();

  profiles \= computed\<{ offensive: TeamProfile, defensive: TeamProfile } | null\>(() \=\> {  
    const team \= this.teamAbbr();  
    const currentRoster \= this.roster();  
    if (team && currentRoster.length \> 0\) {  
      return this.analyticsService.getTeamProfiles(team, currentRoster);  
    }  
    return null;  
  });

  splits \= computed\<TeamSplits | null\>(() \=\> {  
    const team \= this.teamAbbr();  
    if (team) {  
      return this.analyticsService.calculateTeamSplits(team);  
    }  
    return null;  
  });  
}  
// \--- END OF FILE src/components/analytics-panel.component.ts \---

// \--- START OF FILE src/components/chart.component.ts \---  
import { Component, input, viewChild, ElementRef, afterNextRender, OnDestroy } from '@angular/core';  
import { CommonModule } from '@angular/common';

declare var Chart: any; // Using Chart.js from CDN

@Component({  
  selector: 'app-chart',  
  standalone: true,  
  imports: \[CommonModule\],  
  template: \`  
    \<div class="relative w-full h-64 mt-2"\>  
      \<canvas \#canvas\>\</canvas\>  
    \</div\>  
  \`,  
  styles: \[\`  
    :host { display: block; }  
  \`\]  
})  
export class ChartComponent implements OnDestroy {  
  chartConfig \= input.required\<any\>();  
  canvas \= viewChild.required\<ElementRef\<HTMLCanvasElement\>\>('canvas');  
    
  private chartInstance: any;

  constructor() {  
    afterNextRender(() \=\> {  
        this.createChart();  
    });  
  }

  ngOnDestroy(): void {  
    this.chartInstance?.destroy();  
  }

  private createChart(): void {  
    if (this.chartInstance) {  
      this.chartInstance.destroy();  
    }  
    const ctx \= this.canvas().nativeElement.getContext('2d');  
    if (\!ctx) return;

    this.chartInstance \= new Chart(ctx, this.chartConfig());  
  }  
}  
// \--- END OF FILE src/components/chart.component.ts \---

// \--- START OF FILE src/components/game-dashboard.component.ts \---  
import { Component, inject, computed, signal, output } from '@angular/core';  
import { CommonModule } from '@angular/common';  
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';  
import { ModelDataService } from '../services/model-data.service';  
import { ConfigService } from '../services/config.service';  
import { HistoryService } from '../services/history.service';  
import { AlchemistReportComponent } from './alchemist-report.component';  
import { AlchemistService, AlchemistBet } from '../services/alchemist.service';  
import { TelegramService } from '../services/telegram.service';  
import { LUDI\_LOGO\_BASE64 } from '../assets/logo';

@Component({  
  selector: 'app-game-dashboard',  
  standalone: true,  
  imports: \[CommonModule, AlchemistReportComponent\],  
  template: \`  
    \<div class="h-full flex flex-col bg-transparent"\>  
      \<div class="p-4 border-b border-sky-500/10"\>  
        \<div class="flex items-center justify-between mb-4"\>  
            \<button (click)="goHome()" class="text-left group"\>  
              \<h1 class="text-xl font-bold text-white tracking-tight flex items-center gap-3"\>  
                \<img \[src\]="ludiLogo" alt="Ludi Informatio Logo" class="w-8 h-8 group-hover:scale-105 transition-transform"\>  
                  
                \<\!-- Dynamic Branding from Config \--\>  
                \<span class="uppercase tracking-wider text-base group-hover:text-amber-400 transition-colors"\>{{configService.brandHeader()}}\</span\>  
              \</h1\>  
            \</button\>  
            \<button (click)="close.emit()" class="lg:hidden text-slate-400 hover:text-white text-3xl leading-none"\>\&times;\</button\>  
        \</div\>  
          
        \<div class="grid grid-cols-2 gap-2"\>  
            \<button (click)="generateReport()" \[disabled\]="alchemistService.isGenerating()"  
                  class="w-full bg-amber-600 hover:bg-amber-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg text-sm transition-colors flex items-center justify-center gap-2 shadow-lg shadow-amber-950/50 border border-amber-500/50"\>  
            @if (alchemistService.isGenerating()) {  
              \<span class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"\>\</span\>  
              \<span\>Generating...\</span\>  
            } @else {  
              \<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"\>\<path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" /\>\<path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd" /\>\</svg\>  
              \<span\>Briefing\</span\>  
            }  
            \</button\>

             \<button (click)="testTelegram()" \[disabled\]="isTestingTelegram()"  
                  class="w-full bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg text-sm transition-colors flex items-center justify-center gap-2 border border-slate-600"\>  
            @if (isTestingTelegram()) {  
              \<span class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"\>\</span\>  
              \<span\>Testing...\</span\>  
            } @else {  
              \<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"\>\<path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.428A1 1 0 009.894 15V4a1 1 0 00-1-1h-1a1 1 0 00-1 1v11.586l-2.293-2.293a1 1 0 00-1.414 1.414l3.5 3.5a1 1 0 001.414 0l3.5-3.5a1 1 0 00-1.414-1.414L10.894 15V4a1 1 0 00-1-1h-1a1 1 0 00-1 1v7.586l5.293 5.293a1 1 0 001.414-1.414l-7-14z" /\>\</svg\>  
              \<span\>Test\</span\>  
            }  
            \</button\>  
        \</div\>  
      \</div\>  
        
      \<\!-- Game List \--\>  
      \<div class="flex-1 overflow-y-auto"\>  
        @if (games().length \> 0\) {  
          \<div class="divide-y divide-sky-500/10"\>  
            @for (game of games(); track game.id) {  
              \<div   
                (click)="dataService.setActiveGame(game.id)"  
                class="p-4 cursor-pointer transition-colors relative"  
                \[class.bg-amber-500/10\]="game.id \=== dataService.activeGameId()"  
                \[class.hover:bg-slate-800/50\]="game.id \!== dataService.activeGameId()"  
              \>  
                @if(game.id \=== dataService.activeGameId()) {  
                   \<div class="absolute inset-y-0 left-0 w-1 bg-amber-400"\>\</div\>  
                }  
                \<div class="flex justify-between items-center mb-1"\>  
                  \<span class="font-bold text-sm text-white"\>{{game.awayTeam}} @ {{game.homeTeam}}\</span\>  
                  \<span class="text-xs font-mono text-slate-400"\>{{game.time}}\</span\>  
                \</div\>  
                \<div class="flex justify-between items-center text-xs text-slate-400"\>  
                  \<span\>Total: {{game.total}}\</span\>  
                  \<span \[class.text-red-400\]="game.spread \< 0" \[class.text-emerald-400\]="game.spread \> 0"\>  
                    {{game.homeTeam}} {{game.spread \> 0 ? '+' : ''}}{{game.spread}}  
                  \</span\>  
                \</div\>  
              \</div\>  
            }  
          \</div\>  
        } @else {  
          \<div class="p-8 text-center text-slate-500 text-sm"\>  
            \<p\>No games on the slate.\</p\>  
          \</div\>  
        }  
      \</div\>

      \<\!-- Footer with DB Status \--\>  
      \<div class="p-2 border-t border-sky-500/10 text-center text-\[10px\] text-slate-600 font-mono"\>  
        \<p\>{{ historyService.dbStatus() }}\</p\>  
      \</div\>  
    \</div\>  
  \`,  
  styles: \[\`  
    :host {   
      display: block;   
      height: 100%;  
      contain: layout paint;   
    }  
  \`\]  
})  
export class GameDashboardComponent {  
  dataService \= inject(ModelDataService);  
  configService \= inject(ConfigService);  
  historyService \= inject(HistoryService);  
  alchemistService \= inject(AlchemistService);  
  telegramService \= inject(TelegramService);  
  sanitizer: DomSanitizer \= inject(DomSanitizer);  
    
  close \= output();

  games \= this.dataService.games;  
  ludiLogo: SafeResourceUrl;

  isTestingTelegram \= signal(false);

  constructor() {  
    this.ludiLogo \= this.sanitizer.bypassSecurityTrustResourceUrl(LUDI\_LOGO\_BASE64);  
  }

  generateReport() {  
    this.alchemistService.generateReport();  
  }

  async testTelegram() {  
    this.isTestingTelegram.set(true);  
    await this.telegramService.sendTestMessage();  
    this.isTestingTelegram.set(false);  
  }

  goHome(): void {  
    this.dataService.activeGameId.set(null);  
  }  
}  
// \--- END OF FILE src/components/game-dashboard.component.ts \---

// \--- START OF FILE src/components/home-dashboard.component.ts \---  
import { Component, computed, inject, signal } from '@angular/core';  
import { CommonModule, DecimalPipe } from '@angular/common';  
import { LUDI\_LOGO\_BASE64 } from '../assets/logo';  
import { StreakService, PlayerStreak } from '../services/streak.service';  
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

type Period \= 5 | 10 | 15;

@Component({  
  selector: 'app-home-dashboard',  
  standalone: true,  
  imports: \[CommonModule, DecimalPipe\],  
  template: \`  
    \<div class="h-full w-full flex flex-col items-center justify-center p-4 lg:p-8 overflow-y-auto"\>  
      \<div class="w-48 h-48 flex items-center justify-center animate-soft-pulse mb-4"\>  
        \<img \[src\]="ludiLogo" alt="Ludi Informatio Logo" class="w-32 h-32 opacity-20"\>  
      \</div\>  
      \<h2 class="text-2xl font-bold text-slate-200"\>Welcome to Ludi Informatio\</h2\>  
      \<p class="text-slate-400 mb-8"\>Select a game to load the Playbook or view league-wide hot streaks below.\</p\>

      \<div class="w-full max-w-4xl bg-slate-900/50 border border-slate-800 rounded-lg p-4"\>  
        \<\!-- Tabs \--\>  
        \<div class="flex items-center justify-center border-b border-slate-700/50 mb-4"\>  
          @for(period of periods; track period) {  
            \<button   
              (click)="activePeriod.set(period)"  
              class="px-4 py-2 text-sm font-bold transition-colors border-b-2"  
              \[class.text-amber-400\]="activePeriod() \=== period"  
              \[class.border-amber-400\]="activePeriod() \=== period"  
              \[class.border-transparent\]="activePeriod() \!== period"  
              \[class.text-slate-400\]="activePeriod() \!== period"  
              \[class.hover:text-amber-300\]="activePeriod() \!== period"  
            \>  
              Last {{period}} Games  
            \</button\>  
          }  
        \</div\>

        \<\!-- Content \--\>  
        @if (streaks()) {  
          \<div class="grid grid-cols-1 md:grid-cols-3 gap-4"\>  
            \<\!-- Points \--\>  
            \<div class="bg-slate-800/40 p-3 rounded-md"\>  
              \<h4 class="font-bold text-amber-400 text-center mb-2"\>Points\</h4\>  
              \<ul class="space-y-2 text-xs"\>  
                @for (p of streaks()?.pts; track p.name) {  
                  \<li class="flex justify-between items-center bg-slate-900/50 p-2 rounded"\>  
                    \<span class="font-medium text-slate-200 truncate"\>{{ p.name }} \<span class="text-slate-500 text-\[10px\]"\>{{p.team}}\</span\>\</span\>  
                    \<span class="font-mono font-bold text-white"\>{{ p.avgStat | number:'1.1-1' }}\</span\>  
                  \</li\>  
                }  
              \</ul\>  
            \</div\>  
            \<\!-- Rebounds \--\>  
            \<div class="bg-slate-800/40 p-3 rounded-md"\>  
              \<h4 class="font-bold text-amber-400 text-center mb-2"\>Rebounds\</h4\>  
              \<ul class="space-y-2 text-xs"\>  
                @for (p of streaks()?.reb; track p.name) {  
                  \<li class="flex justify-between items-center bg-slate-900/50 p-2 rounded"\>  
                    \<span class="font-medium text-slate-200 truncate"\>{{ p.name }} \<span class="text-slate-500 text-\[10px\]"\>{{p.team}}\</span\>\</span\>  
                    \<span class="font-mono font-bold text-white"\>{{ p.avgStat | number:'1.1-1' }}\</span\>  
                  \</li\>  
                }  
              \</ul\>  
            \</div\>  
            \<\!-- Assists \--\>  
            \<div class="bg-slate-800/40 p-3 rounded-md"\>  
              \<h4 class="font-bold text-amber-400 text-center mb-2"\>Assists\</h4\>  
              \<ul class="space-y-2 text-xs"\>  
                @for (p of streaks()?.ast; track p.name) {  
                  \<li class="flex justify-between items-center bg-slate-900/50 p-2 rounded"\>  
                    \<span class="font-medium text-slate-200 truncate"\>{{ p.name }} \<span class="text-slate-500 text-\[10px\]"\>{{p.team}}\</span\>\</span\>  
                    \<span class="font-mono font-bold text-white"\>{{ p.avgStat | number:'1.1-1' }}\</span\>  
                  \</li\>  
                }  
              \</ul\>  
            \</div\>  
          \</div\>  
        }  
      \</div\>  
      \<p class="text-xs text-slate-700 mt-4"\>LUDI INFORMATIO // BETA 1.3\</p\>  
    \</div\>  
  \`,  
  styles: \`  
    :host {  
      display: flex;  
      height: 100%;  
      width: 100%;  
    }  
    .border-b-2 {  
      border-bottom-width: 2px;  
    }  
  \`  
})  
export class HomeDashboardComponent {  
  streakService \= inject(StreakService);  
  // FIX: Explicitly type DomSanitizer to resolve type inference issue.  
  sanitizer: DomSanitizer \= inject(DomSanitizer);  
    
  ludiLogo: SafeResourceUrl;  
  periods: Period\[\] \= \[5, 10, 15\];  
  activePeriod \= signal\<Period\>(5);

  streaks \= computed(() \=\> {  
    const period \= this.activePeriod();  
    return {  
      pts: this.streakService.getTopPerformers('PTS', period),  
      reb: this.streakService.getTopPerformers('REB', period),  
      ast: this.streakService.getTopPerformers('AST', period),  
    };  
  });

  constructor() {  
    this.ludiLogo \= this.sanitizer.bypassSecurityTrustResourceUrl(LUDI\_LOGO\_BASE64);  
  }  
}  
// \--- END OF FILE src/components/home-dashboard.component.ts \---

// \--- START OF FILE src/components/lens.component.ts \---  
import { Component, output, signal, viewChild, ElementRef, effect, inject, computed } from '@angular/core';  
import { CommonModule } from '@angular/common';  
import { FormsModule } from '@angular/forms';  
import { GameModel, Player } from '../services/model-data.service';  
import { LensService, Message } from '../services/lens.service';  
import { ChartComponent } from './chart.component';  
import { TelegramService } from '../services/telegram.service';  
import { LensStateService } from '../services/lens-state.service';

@Component({  
  selector: 'app-lens',  
  standalone: true,  
  imports: \[CommonModule, FormsModule, ChartComponent\],  
  template: \`  
    \<div class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 animate-in fade-in-25" (click)="lensStateService.close()"\>\</div\>  
    \<div   
      class="fixed inset-y-4 right-4 w-\[600px\] max-w-\[95vw\] bg-slate-900 rounded-lg border border-slate-700 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right-8 duration-300"  
      \[class.contain-content\]="true"\>  
        
      \<\!-- Header \--\>  
      \<div class="p-4 border-b border-slate-800 flex justify-between items-center flex-shrink-0"\>  
        \<div\>  
          \<h2 class="text-lg font-bold text-white flex items-center gap-2"\>  
            \<span class="text-xl"\>💡\</span\> Ludi Lens  
          \</h2\>  
          \<p class="text-xs text-slate-500"\>AI Research Assistant\</p\>  
        \</div\>  
        \<button (click)="lensStateService.close()" class="text-slate-500 hover:text-white transition-colors text-2xl leading-none"\>\&times;\</button\>  
      \</div\>

      \<\!-- Chat History \--\>  
      \<div \#chatContainer class="flex-1 overflow-y-auto p-4 space-y-4"\>  
        @for(message of messages(); track $index) {  
          \<div class="flex" \[class.justify-end\]="message.author \=== 'user'"\>  
            \<div   
              class="max-w-\[85%\] rounded-lg px-4 py-2 relative group"  
              \[class.bg-indigo-600\]="message.author \=== 'user'"  
              \[class.text-white\]="message.author \=== 'user'"  
              \[class.bg-slate-800\]="message.author \=== 'ai'"  
              \[class.text-slate-200\]="message.author \=== 'ai'"  
            \>  
              \<div class="prose prose-invert prose-sm max-w-none whitespace-pre-line leading-relaxed" \[innerHTML\]="message.content"\>\</div\>  
              @if(message.chartData) {  
                \<app-chart \[chartConfig\]="message.chartData"\>\</app-chart\>  
              }

              @if (message.author \=== 'ai' && $index \> 0\) {  
                \<button   
                  (click)="sendMessageToTelegram(message, $index)"   
                  \[disabled\]="sendingMessageIndex() \=== $index"  
                  class="absolute top-1 right-1 bg-slate-700/50 hover:bg-slate-600 rounded-full p-1 text-slate-400 hover:text-white transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"  
                  title="Send to Telegram"\>  
                  @if (sendingMessageIndex() \=== $index) {  
                    \<span class="w-3 h-3 block border-2 border-white border-t-transparent rounded-full animate-spin"\>\</span\>  
                  } @else {  
                    \<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"\>  
                        \<path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.428A1 1 0 009.894 15V4a1 1 0 00-1-1h-1a1 1 0 00-1 1v11.586l-2.293-2.293a1 1 0 00-1.414 1.414l3.5 3.5a1 1 0 001.414 0l3.5-3.5a1 1 0 00-1.414-1.414L10.894 15V4a1 1 0 00-1-1h-1a1 1 0 00-1 1v7.586l5.293 5.293a1 1 0 001.414-1.414l-7-14z" /\>  
                    \</svg\>  
                  }  
                \</button\>  
              }  
            \</div\>  
          \</div\>  
        }  
        @if(isLoading()) {  
           \<div class="flex justify-start"\>  
             \<div class="max-w-\[85%\] rounded-lg px-4 py-2 bg-slate-800 text-slate-200"\>  
                \<div class="flex items-center gap-2"\>  
                    \<span class="w-2 h-2 bg-indigo-400 rounded-full animate-pulse"\>\</span\>  
                    \<span class="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" style="animation-delay: 0.2s;"\>\</span\>  
                    \<span class="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" style="animation-delay: 0.4s;"\>\</span\>  
                \</div\>  
             \</div\>  
           \</div\>  
        }  
      \</div\>

      \<\!-- Input Form \--\>  
      \<div class="p-4 border-t border-slate-800 flex-shrink-0"\>  
        \<form (ngSubmit)="sendMessage()"\>  
          \<div class="flex items-center gap-2"\>  
            \<input   
              type="text"  
              \[ngModel\]="userInput()"  
              (ngModelChange)="userInput.set($event)"  
              name="userInput"  
              placeholder="e.g., LeBron James points last 10 games"  
              class="w-full bg-slate-800 border-slate-700 rounded-md text-sm placeholder:text-slate-500 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"  
              \[disabled\]="isLoading()"\>  
            \<button   
              type="submit"  
              \[disabled\]="isLoading() || userInput().trim() \=== ''"  
              class="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-md text-sm transition-colors"\>  
              Send  
            \</button\>  
          \</div\>  
        \</form\>  
      \</div\>  
    \</div\>  
  \`,  
   styles: \[\`  
    :host { display: block; }  
    :host ::ng-deep .prose-invert ul { margin-top: 0.5rem; margin-bottom: 0.5rem; }  
    :host ::ng-deep .prose-invert li { margin-top: 0.25rem; margin-bottom: 0.25rem; }  
    :host ::ng-deep .prose-invert p { margin-top: 0.5rem; margin-bottom: 0.5rem; }  
  \`\]  
})  
export class LensComponent {  
  lensService \= inject(LensService);  
  telegramService \= inject(TelegramService);  
  lensStateService \= inject(LensStateService);

  game \= this.lensStateService.gameContext;  
  chatContainer \= viewChild\<ElementRef\<HTMLDivElement\>\>('chatContainer');

  initialMessage \= computed\<Message\>(() \=\> {  
    const g \= this.game();  
    const content \= g  
      ? \`I am Ludi Lens. Ask me about the ${g.awayTeam} @ ${g.homeTeam} game, player trends, or matchups. I can now generate charts for visual analysis.\`  
      : "I am Ludi Lens. Ask me about league-wide trends or player stats.";  
    return { author: 'ai', content };  
  });

  messages \= signal\<Message\[\]\>(\[this.initialMessage()\]);  
  userInput \= signal('');  
  isLoading \= signal(false);  
  sendingMessageIndex \= signal\<number | null\>(null);

  constructor() {  
    effect(() \=\> {  
        // This effect will reset the chat when the initial message changes (i.e., when a new context is set)  
        this.messages.set(\[this.initialMessage()\]);  
        this.scrollToBottom();  
    });

    effect(() \=\> {  
        // This effect just handles scrolling on new messages  
        this.messages();  
        this.scrollToBottom();  
    });  
  }

  async sendMessage() {  
    const query \= this.userInput().trim();  
    if (query \=== '' || this.isLoading()) return;

    this.messages.update(m \=\> \[...m, { author: 'user', content: query }\]);  
    this.userInput.set('');  
    this.isLoading.set(true);  
    this.scrollToBottom();

    const current\_game \= this.game();  
    const fullRoster \= current\_game ? \[...current\_game.homeRoster, ...current\_game.awayRoster\] : \[\];  
    const response \= await this.lensService.ask(query, current\_game, fullRoster);

    // Add AI response to history  
    this.messages.update(m \=\> \[...m, { author: 'ai', content: response.summary, chartData: response.chartData }\]);  
    this.isLoading.set(false);  
  }

  async sendMessageToTelegram(message: Message, index: number) {  
    if (this.sendingMessageIndex() \!== null) return;  
    this.sendingMessageIndex.set(index);  
    try {  
        const userMessage \= this.messages()\[index \- 1\];  
        const subject \= \`AI Research: "${userMessage.content}"\`;  
        await this.telegramService.sendAdHocMessage(message.content, subject);  
    } finally {  
        this.sendingMessageIndex.set(null);  
    }  
  }

  private scrollToBottom(): void {  
    setTimeout(() \=\> {  
      const container \= this.chatContainer()?.nativeElement;  
      if (container) {  
        container.scrollTop \= container.scrollHeight;  
      }  
    }, 0);  
  }  
}  
// \--- END OF FILE src/components/lens.component.ts \---

// \--- START OF FILE src/components/notification-container.component.ts \---  
import { Component, inject } from '@angular/core';  
import { CommonModule } from '@angular/common';  
import { NotificationService } from '../services/notification.service';

@Component({  
  selector: 'app-notification-container',  
  standalone: true,  
  imports: \[CommonModule\],  
  template: \`  
    \<div class="fixed top-4 right-4 z-\[100\] flex flex-col items-end gap-3"\>  
      @for (notification of notificationService.notifications(); track notification.id) {  
        \<div   
          (click)="notificationService.remove(notification.id)"  
          class="w-80 max-w-\[90vw\] bg-slate-800 border rounded-lg shadow-2xl shadow-black/50 cursor-pointer overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300"  
          \[class.border-emerald-500/50\]="notification.type \=== 'success'"  
          \[class.border-sky-500/50\]="notification.type \=== 'info'"  
          \[class.border-amber-500/50\]="notification.type \=== 'warning'"  
          \[class.border-red-500/50\]="notification.type \=== 'error'"  
          \[class.border-slate-700\]="\!notification.type"  
        \>  
          \<div class="flex items-start p-3"\>  
            \<div class="text-xl mr-3 mt-0.5"\>{{ notification.icon }}\</div\>  
            \<div class="flex-1"\>  
              \<p class="text-sm font-medium text-slate-100"\>{{ notification.message }}\</p\>  
            \</div\>  
          \</div\>  
          \<div class="h-1 bg-slate-700/50"\>  
             \<div class="h-1 animate-progress origin-left"  
                \[class.bg-emerald-500\]="notification.type \=== 'success'"  
                \[class.bg-sky-500\]="notification.type \=== 'info'"  
                \[class.bg-amber-500\]="notification.type \=== 'warning'"  
                \[class.bg-red-500\]="notification.type \=== 'error'"  
             \>\</div\>  
          \</div\>  
        \</div\>  
      }  
    \</div\>  
  \`,  
  styles: \`  
    @keyframes progress-bar {  
      from { transform: scaleX(1); }  
      to { transform: scaleX(0); }  
    }  
    .animate-progress {  
      animation: progress-bar 5s linear forwards;  
    }  
  \`  
})  
export class NotificationContainerComponent {  
  notificationService \= inject(NotificationService);  
}  
// \--- END OF FILE src/components/notification-container.component.ts \---

// \--- START OF FILE src/components/playbook.component.ts \---  
import { Component, input, signal, inject, effect, ViewEncapsulation, output } from '@angular/core';  
import { CommonModule } from '@angular/common';  
import { GameModel } from '../services/model-data.service';  
import { PlaybookService } from '../services/playbook.service';  
import { ScenarioStateService } from '../services/scenario-state.service';  
import { WorkflowModuleComponent } from './workflow-module.component';  
import { TelegramService } from '../services/telegram.service';  
import { ModelDataService } from '../services/model-data.service';  
import { LensStateService } from '../services/lens-state.service';

@Component({  
  selector: 'app-playbook',  
  standalone: true,  
  imports: \[CommonModule, WorkflowModuleComponent\],  
  template: \`  
    \<div class="space-y-4 h-full overflow-auto p-6"\>  
      \<div class="bg-slate-900/50 backdrop-blur-sm rounded-lg border border-sky-500/10 p-6"\>  
        \<h3 class="text-xl font-bold text-white mb-4 flex items-center justify-between flex-wrap gap-y-2"\>  
          \<span class="flex items-center gap-2 uppercase tracking-wider text-base"\>  
            \<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"\>  
              \<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /\>  
            \</svg\>  
            Game Playbook  
          \</span\>  
          \<div class="flex items-center gap-2 flex-wrap justify-end"\>  
            \<button (click)="goHome()"  
                    title="Back to Dashboard"  
                    class="bg-white/10 hover:bg-white/20 text-white font-bold py-1 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5"\>  
               \<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"\>  
                  \<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.707-10.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L9.414 11H13a1 1 0 100-2H9.414l1.293-1.293z" clip-rule="evenodd" /\>  
               \</svg\>  
              \<span\>Dashboard\</span\>  
            \</button\>  
            \<button (click)="lensStateService.open(game())"  
                    class="bg-white/10 hover:bg-white/20 text-white font-bold py-1 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5"\>  
              \<span class="text-amber-400 text-sm"\>💡\</span\> AI Research  
            \</button\>  
             \<button (click)="openScenarios.emit()"  
                    class="lg:hidden bg-white/10 hover:bg-white/20 text-white font-bold py-1 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5"\>  
               \<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-amber-400" viewBox="0 0 20 20" fill="currentColor"\>\<path d="M17.293 3.293A8 8 0 002.707 17.293 8 8 0 0017.293 3.293zM9 5a1 1 0 012 0v2h2a1 1 0 110 2h-2v2a1 1 0 11-2 0v-2H7a1 1 0 110-2h2V5z" /\>\</svg\>  
              \<span\>Scenarios\</span\>  
            \</button\>  
            \<button (click)="sendPlaybookToTelegram()" \[disabled\]="isSendingToTelegram() || \!playbookContent()"  
                    class="bg-white/10 hover:bg-white/20 text-white font-bold py-1 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"\>  
              @if (isSendingToTelegram()) {  
                \<span class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"\>\</span\>  
              } @else {  
                \<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"\>\<path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.428A1 1 0 009.894 15V4a1 1 0 00-1-1h-1a1 1 0 00-1 1v11.586l-2.293-2.293a1 1 0 00-1.414 1.414l3.5 3.5a1 1 0 001.414 0l3.5-3.5a1 1 0 00-1.414-1.414L10.894 15V4a1 1 0 00-1-1h-1a1 1 0 00-1 1v7.586l5.293 5.293a1 1 0 001.414-1.414l-7-14z" /\>\</svg\>  
              }  
            \</button\>  
            @if(playbookContent()) {  
              \<button (click)="generatePlaybook()" \[disabled\]="isGenerating()"  
                      class="bg-white/10 hover:bg-white/20 text-white font-bold py-1 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-2"  
                      \[class.bg-amber-600\]="isStale()" \[class.hover:bg-amber-500\]="isStale()" \[class.animate-pulse\]="isStale()"\>  
                @if (isGenerating()) {  
                  \<span class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"\>\</span\>  
                  Updating...  
                } @else {  
                  \<span\>  
                    🔄   
                    @if (isStale()) {  
                      Refresh (Stale)  
                    } @else {  
                      Refresh  
                    }  
                  \</span\>  
                }  
              \</button\>  
            }  
          \</div\>  
        \</h3\>  
        @if (isGenerating() && \!playbookContent()) {  
          \<div class="flex flex-col items-center py-12"\>  
            \<div class="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"\>\</div\>  
            \<p class="text-amber-300 animate-pulse text-sm"\>Synthesizing game script & key narratives...\</p\>  
          \</div\>  
        } @else if (playbookContent()) {  
          \<div class="prose prose-invert prose-sm max-w-none whitespace-pre-line text-slate-300 leading-relaxed \[contain:strict\] \[content-visibility:auto\]" \[innerHTML\]="playbookContent()"\>  
          \</div\>  
        } @else {  
          \<div class="text-center py-8"\>  
            \<button (click)="generatePlaybook()" \[disabled\]="isGenerating()" class="bg-amber-500 text-slate-900 hover:bg-amber-400 px-6 py-2 rounded-lg font-bold shadow-lg shadow-amber-900/40 transition-colors flex items-center justify-center"\>  
              @if(isGenerating()) {  
                \<span class="w-4 h-4 border-2 border-slate-800 border-t-transparent rounded-full animate-spin mr-2"\>\</span\>  
                \<span\>Generating...\</span\>  
              } @else {  
                \<span\>Generate Playbook\</span\>  
              }  
            \</button\>  
            \<p class="text-xs text-slate-500 mt-2"\>Analyzes data to create actionable game notes & narratives.\</p\>  
          \</div\>  
        }  
      \</div\>

      \<\!-- NEW: Workflow Spotlight Module \--\>  
      \<app-workflow-module \[game\]="game()"\>\</app-workflow-module\>

    \</div\>  
  \`,  
  styles: \[\`  
    :host {   
      display: block;   
      height: 100%;   
      contain: content;  
    }  
    :host ::ng-deep .prose-invert h4 {  
        font-size: 0.875rem;  
        font-weight: 700;  
        text-transform: uppercase;  
        letter-spacing: 0.05em;  
        color: \#fbbf24; /\* amber-400 \*/  
        border-bottom: 1px solid \#334155; /\* slate-700 \*/  
        padding-bottom: 0.5rem;  
        margin-bottom: 1rem;  
    }  
    :host ::ng-deep .prose-invert hr {  
      border-color: \#334155; /\* slate-700 \*/  
      margin-top: 1.5rem;  
      margin-bottom: 1.5rem;  
    }  
    ::-webkit-scrollbar { width: 8px; }  
    ::-webkit-scrollbar-track { background: \#0f172a; }  
    ::-webkit-scrollbar-thumb { background: \#334155; border-radius: 4px; }  
    ::-webkit-scrollbar-thumb:hover { background: \#475569; }  
  \`\],  
  encapsulation: ViewEncapsulation.None,  
})  
export class PlaybookComponent {  
  playbookService \= inject(PlaybookService);  
  scenarioState \= inject(ScenarioStateService);  
  telegramService \= inject(TelegramService);  
  dataService \= inject(ModelDataService);  
  lensStateService \= inject(LensStateService);  
    
  game \= input.required\<GameModel\>();  
  openScenarios \= output();

  isGenerating \= signal(false);  
  isSendingToTelegram \= signal(false);  
  playbookContent \= signal\<string | null\>(null);  
  isStale \= signal(false);

  constructor() {  
    // Effect to reset state when the game changes.  
    effect(() \=\> {  
      this.game(); // Establish dependency on the game input  
      this.playbookContent.set(null);  
      this.isGenerating.set(false);  
      this.isStale.set(false);  
    });

    // Effect to detect when the playbook becomes stale due to scenario changes.  
    effect(() \=\> {  
      this.scenarioState.scenarioRoster(); // Establish dependency on scenario changes  
        
      // If content has already been generated, any subsequent roster change makes it stale.  
      if (this.playbookContent()) {  
        this.isStale.set(true);  
      }  
    });  
  }

  async generatePlaybook() {  
    this.isStale.set(false); // The playbook will no longer be stale after this generation starts.  
    this.isGenerating.set(true);  
    this.playbookContent.set(''); // Clear previous content and prepare for streaming

    const onChunk \= (chunk: string) \=\> {  
      this.playbookContent.update(current \=\> (current || '') \+ chunk);  
    };

    const onError \= (errorMsg: string) \=\> {  
      this.playbookContent.update(current \=\> (current || '') \+ \`\\n\\n\<span class="text-red-500"\>${errorMsg}\</span\>\`);  
    };

    try {  
      await this.playbookService.streamPlaybook(this.game(), this.scenarioState.scenarioRoster(), onChunk, onError);  
    } finally {  
      this.isGenerating.set(false);  
    }  
  }

  async sendPlaybookToTelegram() {  
    const content \= this.playbookContent();  
    if (\!content) return;

    this.isSendingToTelegram.set(true);  
    try {  
      const subject \= \`Game Notes: ${this.game().awayTeam} @ ${this.game().homeTeam}\`;  
      await this.telegramService.sendAdHocMessage(content, subject);  
    } finally {  
      this.isSendingToTelegram.set(false);  
    }  
  }

  goHome(): void {  
    this.dataService.activeGameId.set(null);  
  }  
}  
// \--- END OF FILE src/components/playbook.component.ts \---

// \--- START OF FILE src/components/scenario-control.component.ts \---  
import { Component, inject, output } from '@angular/core';  
import { CommonModule } from '@angular/common';  
import { FormsModule } from '@angular/forms';  
import { ScenarioStateService } from '../services/scenario-state.service';  
import { Player } from '../services/model-data.service';  
import { SparklineComponent } from './sparkline.component';

@Component({  
  selector: 'app-scenario-control',  
  standalone: true,  
  imports: \[CommonModule, FormsModule, SparklineComponent\],  
  template: \`  
    \<div class="h-full flex flex-col bg-slate-900/80 backdrop-blur-md border-l border-sky-500/10"\>  
      \<div class="p-4 border-b border-sky-500/10 flex-shrink-0"\>  
        \<div class="flex items-center justify-between"\>  
          \<h3 class="text-lg font-bold text-white flex items-center gap-2 uppercase tracking-wider text-base"\>  
            \<span class="text-amber-400"\>⚡\</span\> Scenarios  
          \</h3\>  
          \<button (click)="close.emit()" class="lg:hidden text-slate-400 hover:text-white text-3xl leading-none"\>\&times;\</button\>  
        \</div\>  
        \<p class="text-xs text-slate-400 mt-1"\>Toggle players OUT to see live impact on projections.\</p\>  
      \</div\>

      @if (game(); as g) {  
        \<div class="p-4 flex-shrink-0 border-b border-sky-500/10"\>  
           \<div class="grid grid-cols-2 gap-4"\>  
             \<div class="bg-slate-900/50 p-3 rounded border border-slate-700/50 flex items-center justify-between"\>  
               \<div class="text-xs text-slate-300"\>  
                 \<div class="font-bold text-white"\>{{g.homeTeam}}\</div\>  
                 \<div class="text-\[10px\] uppercase text-slate-500"\>Schedule Spot\</div\>  
               \</div\>  
               \<label class="flex items-center gap-2 cursor-pointer"\>  
                 \<input type="checkbox" \[ngModel\]="state.homeIsB2B()" (ngModelChange)="state.homeIsB2B.set($event)" class="w-4 h-4 rounded border-slate-600 bg-slate-800 text-amber-500 focus:ring-0"\>  
                 \<span class="text-xs font-bold" \[class.text-red-400\]="state.homeIsB2B()" \[class.text-slate-500\]="\!state.homeIsB2B()"\>B2B\</span\>  
               \</label\>  
             \</div\>  
             \<div class="bg-slate-900/50 p-3 rounded border border-slate-700/50 flex items-center justify-between"\>  
               \<div class="text-xs text-slate-300"\>  
                 \<div class="font-bold text-white"\>{{g.awayTeam}}\</div\>  
                 \<div class="text-\[10px\] uppercase text-slate-500"\>Schedule Spot\</div\>  
               \</div\>  
               \<label class="flex items-center gap-2 cursor-pointer"\>  
                 \<input type="checkbox" \[ngModel\]="state.awayIsB2B()" (ngModelChange)="state.awayIsB2B.set($event)" class="w-4 h-4 rounded border-slate-600 bg-slate-800 text-amber-500 focus:ring-0"\>  
                 \<span class="text-xs font-bold" \[class.text-red-400\]="state.awayIsB2B()" \[class.text-slate-500\]="\!state.awayIsB2B()"\>B2B\</span\>  
               \</label\>  
             \</div\>  
           \</div\>  
           @if (state.outPlayerIds().size \> 0\) {  
              \<div class="mt-4 text-right"\>  
                 \<button (click)="state.resetScenarios()" class="text-\[10px\] bg-slate-700 hover:bg-slate-600 text-white px-2 py-1 rounded"\>Reset All Toggles\</button\>  
              \</div\>  
           }  
        \</div\>  
      }

      \<div class="flex-1 overflow-y-auto"\>  
        \<div class="grid grid-cols-12 bg-slate-950/50 px-4 py-2 text-\[10px\] uppercase text-slate-400 font-bold tracking-wider sticky top-0 backdrop-blur-sm z-10 border-b border-sky-500/10"\>  
           \<div class="col-span-1"\>Out\</div\>  
           \<div class="col-span-5"\>Player\</div\>  
           \<div class="col-span-3 text-center"\>Trend\</div\>  
           \<div class="col-span-3 text-right"\>Proj / Δ\</div\>  
        \</div\>

        @for (player of scenarioRoster(); track player.id) {  
          \<div class="grid grid-cols-12 px-4 py-2.5 items-center border-b border-sky-500/10 hover:bg-slate-800/30 transition-colors" \[class.opacity-40\]="player.isOut" \[class.bg-red-900/20\]="player.isOut"\>  
             \<div class="col-span-1"\>  
               \<button (click)="state.togglePlayerOut(player.id)" class="w-6 h-6 flex items-center justify-center rounded-full hover:bg-slate-700 transition-colors" \[class.text-red-500\]="\!player.isOut" \[class.text-emerald-400\]="player.isOut"\>  
                 {{ player.isOut ? '↩' : '✖' }}  
               \</button\>  
             \</div\>  
             \<div class="col-span-5 font-medium text-white text-xs truncate pr-2"\>  
               {{player.name}}  
             \</div\>  
             \<div class="col-span-3"\>  
                \<app-sparkline \[color\]="getDelta(player, 'pts') \> 0 ? '\#fbbf24' : '\#64748b'"\>\</app-sparkline\>  
             \</div\>  
             \<div class="col-span-3 text-right text-\[11px\] font-mono p-1 rounded-md" \[class\]="getDeltaClasses(player)"\>  
                \<span class="font-bold"\>{{ player.projected?.pts | number:'1.1-1' }}\</span\>  
                @if (\!player.isOut && getDelta(player, 'pts') \!== 0\) {  
                  \<span class="ml-1 text-\[9px\]"\>  
                    ({{getDelta(player, 'pts') \> 0 ? '+' : ''}}{{getDelta(player, 'pts') | number:'1.1-1'}})  
                  \</span\>  
                }  
             \</div\>  
          \</div\>  
        }  
      \</div\>  
    \</div\>  
  \`,  
  styles: \[\`  
    :host {  
      display: block;  
      height: 100%;  
      contain: layout paint;  
    }  
  \`\]  
})  
export class ScenarioControlComponent {  
  state \= inject(ScenarioStateService);  
  game \= this.state.game;  
  scenarioRoster \= this.state.scenarioRoster;  
  close \= output();

  getDelta(player: Player, stat: 'pts' | 'min'): number {  
      const basePlayer \= this.state.baseRoster().find(p \=\> p.id \=== player.id);  
      if (\!basePlayer || \!basePlayer.projected) return 0;  
        
      const base \= stat \=== 'pts' ? basePlayer.projected.pts : basePlayer.projected.min;  
      const proj \= stat \=== 'pts' ? player.projected?.pts : player.projected?.min;  
        
      if (proj \=== undefined || base \=== undefined) return 0;  
      return proj \- base;  
  }

  getDeltaClasses(player: Player): string {  
    if (player.isOut) return 'text-slate-500';  
      
    const delta \= this.getDelta(player, 'pts');  
    if (delta \> 2.5) return 'bg-emerald-500/20 text-emerald-300';  
    if (delta \> 0\) return 'bg-emerald-500/10 text-emerald-400';  
    if (delta \< \-2.5) return 'bg-red-500/20 text-red-300';  
    if (delta \< 0\) return 'bg-red-500/10 text-red-400';  
      
    return 'text-white';  
  }  
}  
// \--- END OF FILE src/components/scenario-control.component.ts \---

// \--- START OF FILE src/components/sparkline.component.ts \---  
import { Component, input } from '@angular/core';  
import { CommonModule } from '@angular/common';

@Component({  
  selector: 'app-sparkline',  
  standalone: true,  
  imports: \[CommonModule\],  
  template: \`  
    \<svg   
      class="w-full h-4"   
      viewBox="0 0 100 20"   
      preserveAspectRatio="none"   
      xmlns="http://www.w3.org/2000/svg"  
    \>  
      \<path   
        d="M 0,15 L 20,10 L 40,12 L 60,5 L 80,8 L 100,12"   
        \[attr.stroke\]="color()"   
        stroke-width="2"   
        fill="none"   
        stroke-linejoin="round"   
        stroke-linecap="round"  
      /\>  
    \</svg\>  
  \`,  
  styles: \[\`  
    :host {   
      display: block;   
      width: 100%;  
    }  
  \`\]  
})  
export class SparklineComponent {  
  color \= input\<string\>('\#64748b'); // Default to a neutral slate color  
}  
// \--- END OF FILE src/components/sparkline.component.ts \---

// \--- START OF FILE src/components/synergy-panel.component.ts \---  
import { Component, computed, effect, inject, input, signal } from '@angular/core';  
import { CommonModule, DecimalPipe } from '@angular/common';  
import { Player } from '../services/model-data.service';  
import { SynergyService, WowyImpact } from '../services/synergy.service';  
import { FormsModule } from '@angular/forms';

@Component({  
  selector: 'app-synergy-panel',  
  standalone: true,  
  imports: \[CommonModule, FormsModule, DecimalPipe\],  
  template: \`  
    \<div class="bg-slate-800/40 p-4 rounded-lg border border-slate-700/50 h-full"\>  
      \<h4 class="font-bold text-slate-300 text-sm mb-3"\>Player Synergy (WOWY)\</h4\>

      @if (roster().length \> 0\) {  
        \<\!-- Player Selector \--\>  
        \<div class="mb-3"\>  
          \<select   
            \[ngModel\]="selectedPlayerId()"   
            (ngModelChange)="selectPlayerById($event)"  
            class="w-full bg-slate-800 border-slate-700 rounded-md text-xs py-1.5 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"  
          \>  
            \<option \[value\]="null" disabled\>Select Player to Analyze\</option\>  
            @for (player of roster(); track player.id) {  
              \<option \[value\]="player.id"\>{{ player.name }}\</option\>  
            }  
          \</select\>  
        \</div\>

        @if (selectedPlayer(); as p) {  
          \<div class="space-y-2"\>  
            @if (wowyImpacts() && wowyImpacts()\!.length \> 0\) {  
              @for(impact of wowyImpacts(); track impact.teammateId) {  
                \<div class="bg-slate-900/50 p-2 rounded"\>  
                  \<p class="text-xs font-bold text-white"\>{{ impact.teammateName }}\</p\>  
                  \<p class="text-\[10px\] text-slate-400"\>Impact \<span class="font-bold text-indigo-300"\>WITH\</span\> {{ p.name }} on floor\</p\>  
                  \<div class="grid grid-cols-4 gap-2 mt-1 text-center font-mono text-xs"\>  
                    \<div \[class.text-emerald-400\]="impact.impact.pts \> 0" \[class.text-red-400\]="impact.impact.pts \< 0"\>  
                      \<p class="font-bold"\>{{ impact.impact.pts \> 0 ? '+' : '' }}{{ impact.impact.pts | number:'1.1-1' }}\</p\>  
                      \<p class="text-\[9px\] text-slate-500"\>PTS\</p\>  
                    \</div\>  
                     \<div \[class.text-emerald-400\]="impact.impact.reb \> 0" \[class.text-red-400\]="impact.impact.reb \< 0"\>  
                      \<p class="font-bold"\>{{ impact.impact.reb \> 0 ? '+' : '' }}{{ impact.impact.reb | number:'1.1-1' }}\</p\>  
                      \<p class="text-\[9px\] text-slate-500"\>REB\</p\>  
                    \</div\>  
                     \<div \[class.text-emerald-400\]="impact.impact.ast \> 0" \[class.text-red-400\]="impact.impact.ast \< 0"\>  
                      \<p class="font-bold"\>{{ impact.impact.ast \> 0 ? '+' : '' }}{{ impact.impact.ast | number:'1.1-1' }}\</p\>  
                      \<p class="text-\[9px\] text-slate-500"\>AST\</p\>  
                    \</div\>  
                     \<div \[class.text-emerald-400\]="impact.impact.fgPct \> 0" \[class.text-red-400\]="impact.impact.fgPct \< 0"\>  
                      \<p class="font-bold"\>{{ impact.impact.fgPct \> 0 ? '+' : '' }}{{ impact.impact.fgPct | number:'1.1-1' }}%\</p\>  
                      \<p class="text-\[9px\] text-slate-500"\>FG%\</p\>  
                    \</div\>  
                  \</div\>  
                \</div\>  
              }  
            } @else {  
              \<div class="text-center py-8"\>  
                 \<p class="text-xs text-slate-500"\>Not enough historical data to calculate synergy for {{p.name}}.\</p\>  
              \</div\>  
            }  
          \</div\>  
        } @else {  
          \<div class="text-center py-8"\>  
            \<p class="text-xs text-slate-500"\>Select a player to view their on-court impact on teammates.\</p\>  
          \</div\>  
        }  
      } @else {  
         \<p class="text-center text-slate-500 text-sm"\>No roster data available.\</p\>  
      }  
    \</div\>  
  \`,  
  styles: \[':host { display: block; contain: layout paint; }'\]  
})  
export class SynergyPanelComponent {  
  synergyService \= inject(SynergyService);

  teamAbbr \= input.required\<string\>();  
  roster \= input.required\<Player\[\]\>();

  selectedPlayerId \= signal\<string | null\>(null);  
  selectedPlayer \= computed(() \=\> this.roster().find(p \=\> p.id \=== this.selectedPlayerId()));

  // OPTIMIZED: Converted from an effect to a computed signal.  
  // This is more efficient as it's memoized and only recalculates when dependencies change.  
  wowyImpacts \= computed(() \=\> {  
    const primary \= this.selectedPlayer();  
    const currentRoster \= this.roster();  
    if (primary && currentRoster) {  
      const rotation \= this.synergyService.getRotationMatrix(primary, currentRoster);  
      return rotation  
        .map(teammate \=\> this.synergyService.calculateWowyImpact(teammate, primary))  
        .filter((i): i is WowyImpact \=\> \!\!i); // Filter out nulls  
    }  
    return null;  
  });

  constructor() {  
    // This effect handles a UI-specific side effect: auto-selecting a player.  
    // This is a valid use of an effect.  
    effect(() \=\> {  
      const currentRoster \= this.roster();  
      if (currentRoster && currentRoster.length \> 0\) {  
        const sorted \= \[...currentRoster\].sort((a, b) \=\> (b.stats.l20.fga || 0\) \- (a.stats.l20.fga || 0));  
        // Check if the currently selected player is still in the new roster  
        const currentPlayerStillExists \= currentRoster.some(p \=\> p.id \=== this.selectedPlayerId());  
        if (\!currentPlayerStillExists) {  
            this.selectedPlayerId.set(sorted\[0\].id);  
        }  
      } else {  
        this.selectedPlayerId.set(null);  
      }  
    });  
  }

  selectPlayerById(id: string | null) {  
    this.selectedPlayerId.set(id);  
  }  
}  
// \--- END OF FILE src/components/synergy-panel.component.ts \---

// \--- START OF FILE src/components/workflow-module.component.ts \---  
import { Component, computed, inject, input, signal } from '@angular/core';  
import { CommonModule } from '@angular/common';  
import { GameModel } from '../services/model-data.service';  
import { CalibratorService } from '../services/calibrator.service';  
import { AnalyticsPanelComponent } from './analytics-panel.component';  
import { SynergyPanelComponent } from './synergy-panel.component';

@Component({  
  selector: 'app-workflow-module',  
  standalone: true,  
  imports: \[CommonModule, AnalyticsPanelComponent, SynergyPanelComponent\],  
  template: \`  
    \<div class="bg-slate-900/50 backdrop-blur-sm rounded-lg border border-sky-500/10"\>  
      \<\!-- Header Tabs \--\>  
      \<div class="flex items-center border-b border-sky-500/10 p-2"\>  
        \<h3 class="text-lg font-bold text-white pl-2 pr-4 flex items-center gap-2 uppercase tracking-wider text-base"\>  
          \<span class="text-xl"\>🔬\</span\> Spotlight  
        \</h3\>  
        \<div class="flex items-center gap-1 bg-slate-950/50 p-1 rounded-md"\>  
          \<button  
            (click)="activeTab.set('away')"  
            \[class.bg-slate-700\]="activeTab() \=== 'away'"  
            \[class.text-white\]="activeTab() \=== 'away'"  
            \[class.text-slate-400\]="activeTab() \!== 'away'"  
            class="px-3 py-1 text-xs font-bold rounded transition-colors hover:bg-slate-700"  
          \>  
            {{ game().awayTeam }}  
          \</button\>  
          \<button  
            (click)="activeTab.set('home')"  
            \[class.bg-slate-700\]="activeTab() \=== 'home'"  
            \[class.text-white\]="activeTab() \=== 'home'"  
            \[class.text-slate-400\]="activeTab() \!== 'home'"  
            class="px-3 py-1 text-xs font-bold rounded transition-colors hover:bg-slate-700"  
          \>  
            {{ game().homeTeam }}  
          \</button\>  
        \</div\>  
      \</div\>

      \<\!-- Content \--\>  
      \<div class="p-4"\>  
        @if (activeRoster()) {  
          \<div class="grid grid-cols-1 lg:grid-cols-2 gap-4"\>  
            \<app-analytics-panel   
              \[teamAbbr\]="activeTeamAbbr()"   
              \[roster\]="activeRoster()"  
              \[opponentDefStyle\]="opponentDefStyle()"\>  
            \</app-analytics-panel\>

            \<app-synergy-panel   
              \[teamAbbr\]="activeTeamAbbr()"   
              \[roster\]="activeRoster()"\>  
            \</app-synergy-panel\>  
          \</div\>  
        } @else {  
          \<p class="text-sm text-slate-500 text-center"\>Roster data not available.\</p\>  
        }  
      \</div\>  
    \</div\>  
  \`,  
  styles: \[\`  
    :host {   
        display: block;   
        contain: layout paint;  
    }  
  \`\]  
})  
export class WorkflowModuleComponent {  
  calibratorService \= inject(CalibratorService);

  game \= input.required\<GameModel\>();  
  activeTab \= signal\<'home' | 'away'\>('away');

  activeTeamAbbr \= computed(() \=\> this.activeTab() \=== 'home' ? this.game().homeTeam : this.game().awayTeam);  
    
  activeRoster \= computed(() \=\> {  
    return this.activeTab() \=== 'home' ? this.game().homeRoster : this.game().awayRoster;  
  });

  opponentDefStyle \= computed(() \=\> {  
    const opponentAbbr \= this.activeTab() \=== 'home' ? this.game().awayTeam : this.game().homeTeam;  
    return this.calibratorService.getDefensiveStyle(opponentAbbr);  
  });  
}  
// \--- END OF FILE src/components/workflow-module.component.ts \---

// \--- START OF FILE src/services/alchemist.service.ts \---  
import { Injectable, inject, signal } from '@angular/core';  
import { ModelDataService, GameModel, Player } from './model-data.service';  
import { ScenarioService, SimConfig } from './scenario.service';  
import { NotificationService } from './notification.service';  
import { TelegramService } from './telegram.service';

// Player-specific bet  
export interface PlayerPropBet {  
  type: 'player';  
  name: string;  
  team: string;  
  stat: string; // 'PTS', 'REB', etc.  
  betOn: 'OVER' | 'UNDER';  
  line: number;  
  proj: number;  
  ev: number;  
  units: number;  
  note: string;  
  breakdown: {  
    baseline: number;  
    calibrationNotes: string;  
  };  
}

// Game-level bet (spread, total, etc.)  
export interface GameBet {  
  type: 'spread' | 'total' | 'team\_total';  
  tier: 'gold' | 'silver';  
  gameId: string;  
  homeTeam: string;  
  awayTeam: string;  
  market: string; // e.g., 'Spread', 'Total Points'  
  pick: string;   // e.g., 'LAL \+2.5', 'OVER 225.5'  
  line: number;  
  proj: number;  
  ev: number;  
  units: number;  
  note: string;  
}

export type AlchemistBet \= PlayerPropBet | GameBet;

@Injectable({  
  providedIn: 'root',  
})  
export class AlchemistService {  
  private modelDataService \= inject(ModelDataService);  
  private scenarioService \= inject(ScenarioService);  
  private notificationService \= inject(NotificationService);  
  private telegramService \= inject(TelegramService);

  report \= signal\<AlchemistBet\[\]\>(\[\]);  
  isGenerating \= signal(false);  
  showReport \= signal(false);

  async generateReport(): Promise\<void\> {  
    if (this.isGenerating()) return;

    this.isGenerating.set(true);  
    this.showReport.set(true);  
    this.report.set(\[\]); // Clear previous report while loading

    // \--- Step 1: Run simulations for any games that haven't been processed \---  
    const allGames \= this.modelDataService.games();  
    let allBets: AlchemistBet\[\] \= \[\];  
    for (const game of allGames) {  
      if (game.detailsLoaded && \!game.simResults.postYak) {  
        const baselineRoster \= \[...game.homeRoster, ...game.awayRoster\];  
        this.modelDataService.runSimulation(game.id, 'post', baselineRoster, { home: 1, away: 1 });  
      }  
    }

    // Brief pause to ensure signals can propagate if needed  
    await new Promise(r \=\> setTimeout(r, 50));

    const updatedGames \= this.modelDataService.games();

    for (const game of updatedGames) {  
      if (\!game.detailsLoaded) continue;

      // \--- Step 2: Generate Player Prop Bets \---  
      const gamePlayers \= this.getProjectedPlayers(game);  
      const spread \= Math.abs(game.spread);  
      const blowoutMult \= 1.0 \- (Math.max(0, spread \- 7.0) \* 0.015);

      for (const p of gamePlayers) {  
        if (\!p.projected || p.projected.min \<= 0 || p.status \=== 'Out' || p.isOut) continue;  
          
        if (p.props) {  
            allBets.push(...this.findPlayerPropEdges(p, game, blowoutMult));  
        }  
      }  
        
      // \--- Step 3: Generate Game Line Bets \---  
      if (game.simResults.postYak) {  
        // FIX: Added missing method 'findGameLineEdges'.  
        allBets.push(...this.findGameLineEdges(game));  
      }  
    }  
      
    // \--- Step 4: Final Processing & Sorting \---  
    const highUnitCounts \= new Map\<string, number\>();  
    allBets.forEach(bet \=\> {  
        if (bet.type \=== 'player' && bet.units \>= 1.2) {  
            highUnitCounts.set(bet.name, (highUnitCounts.get(bet.name) || 0\) \+ 1);  
        }  
    });  
    allBets.forEach(bet \=\> {  
        if (bet.type \=== 'player' && (highUnitCounts.get(bet.name) || 0\) \>= 2\) {  
            bet.note \= (bet.note ? bet.note \+ " | " : "") \+ "🔥 CORRELATED SGP";  
        }  
    });

    allBets.sort((a, b) \=\> b.ev \- a.ev);  
      
    this.report.set(allBets);

    // \--- Step 5: Fire Notifications & Send Report \---  
    this.fireInAppNotifications(allBets);  
    this.telegramService.sendReport(allBets);

    this.isGenerating.set(false);  
  }

  closeReport(): void {  
    this.showReport.set(false);  
  }

  private fireInAppNotifications(allBets: AlchemistBet\[\]): void {  
    const diamondPlays \= allBets.filter(b \=\> b.type \=== 'player' && b.ev \>= 10.0).length;  
    const goldPlays \= allBets.filter(b \=\> b.type \=== 'player' && b.ev \>= 5.0 && b.ev \< 10.0).length;  
    const gameLinePlays \= allBets.filter(b \=\> b.type \!== 'player').length;

    if (diamondPlays \> 0\) {  
      this.notificationService.add(\`${diamondPlays} Diamond Play(s) found in briefing\!\`, 'success');  
    } else if (goldPlays \> 0\) {  
      this.notificationService.add(\`✨ ${goldPlays} Gold Play(s) found in briefing.\`, 'info');  
    } else if (gameLinePlays \> 0\) {  
      this.notificationService.add(\`📈 Briefing ready with ${gameLinePlays} game line edge(s).\`, 'info');  
    } else if (allBets.length \> 0\) {  
      this.notificationService.add('📊 Daily Briefing is ready for review.', 'info');  
    }  
  }

  private getProjectedPlayers(game: GameModel): Player\[\] {  
     const simConfig: SimConfig \= {  
        homeTeam: game.homeTeam, awayTeam: game.awayTeam,  
        spread: game.spread, total: game.total, refImpact: game.refereeImpact,  
        isPostYak: true, daysRestHome: 1, daysRestAway: 1,  
      };

      const { homeRosterWithProjections, awayRosterWithProjections } \=  
        this.scenarioService.generateProjections(simConfig, game.homeRoster, game.awayRoster);  
        
      return \[...homeRosterWithProjections, ...awayRosterWithProjections\];  
  }

  // FIX: Completed the implementation of this function which was previously cut off, and added a return statement.  
  private findPlayerPropEdges(p: Player, game: GameModel, blowoutMult: number): PlayerPropBet\[\] {  
      const bets: PlayerPropBet\[\] \= \[\];  
      if (\!p.props) {  
        return bets;  
      }  
      for (const prop of p.props) {  
          // FIX: Added missing methods '\_mapStat' and '\_mapBaselineStat'.  
          const rawVal \= this.\_mapStat(p, prop.market);  
          const baselineVal \= this.\_mapBaselineStat(p, prop.market);

          if (rawVal \=== null || baselineVal \=== null || prop.line \<= 0\) continue;

          const finalProj \= rawVal \* blowoutMult;  
          const line \= prop.line;  
          const edge \= ((finalProj \- line) / line) \* 100;  
            
          if (Math.abs(edge) \>= 5.0) {  
            const betOn \= edge \> 0 ? 'OVER' : 'UNDER';  
            const absEdge \= Math.abs(edge);  
            // Simplified Kelly Criterion for unit sizing  
            const units \= Math.min(2.0, Math.max(0.25, (absEdge / 100\) \* 2.5));

            bets.push({  
              type: 'player',  
              name: p.name,  
              team: p.teamAbbr,  
              stat: this.mapMarketToStat(prop.market),  
              betOn: betOn,  
              line: line,  
              proj: parseFloat(finalProj.toFixed(2)),  
              ev: parseFloat(absEdge.toFixed(1)),  
              units: parseFloat(units.toFixed(2)),  
              note: \`Model projects ${finalProj.toFixed(1)}, line is ${line}. Edge: ${edge.toFixed(1)}%\`,  
              breakdown: {  
                baseline: parseFloat(baselineVal.toFixed(2)),  
                calibrationNotes: p.calibrationNotes || 'None',  
              },  
            });  
          }  
      }  
      return bets;  
  }

  // FIX: Implemented missing method 'findGameLineEdges'.  
  private findGameLineEdges(game: GameModel): GameBet\[\] {  
    const bets: GameBet\[\] \= \[\];  
    const sim \= game.simResults.postYak;  
    if (\!sim) return bets;

    // 1\. Spread Bet  
    const simSpread \= sim.awayScore \- sim.homeScore; // Standard convention: away \- home  
    const lineSpread \= game.spread \* \-1; // Odds are from home team perspective, so flip for standard  
    const spreadEdge \= simSpread \- lineSpread;

    if (Math.abs(spreadEdge) \>= 1.5) { // 1.5 point edge threshold  
      const pick \= spreadEdge \< 0 ? \`${game.homeTeam} ${game.spread \> 0 ? '+' : ''}${game.spread}\` : \`${game.awayTeam} ${game.spread \< 0 ? '+' : ''}${game.spread \* \-1}\`;  
      const ev \= Math.abs(spreadEdge) \* 5; // Heuristic EV  
      const units \= Math.min(1.5, Math.max(0.5, Math.abs(spreadEdge) / 2));  
      const tier \= Math.abs(spreadEdge) \>= 2.5 ? 'gold' : 'silver';

      bets.push({  
        type: 'spread',  
        tier: tier,  
        gameId: game.id,  
        homeTeam: game.homeTeam,  
        awayTeam: game.awayTeam,  
        market: 'Spread',  
        pick: pick,  
        line: game.spread,  
        proj: sim.homeScore \- sim.awayScore, // home perspective proj  
        ev: parseFloat(ev.toFixed(1)),  
        units: parseFloat(units.toFixed(2)),  
        note: \`Model projects a spread of ${(sim.homeScore \- sim.awayScore).toFixed(1)}, line is ${game.spread}.\`  
      });  
    }

    // 2\. Total Bet  
    const totalEdge \= sim.predictedTotal \- game.total;  
    if (Math.abs(totalEdge) \>= 3.0) { // 3 point edge threshold  
        const pick \= totalEdge \> 0 ? \`OVER ${game.total}\` : \`UNDER ${game.total}\`;  
        const ev \= Math.abs(totalEdge) \* 3;  
        const units \= Math.min(1.5, Math.max(0.5, Math.abs(totalEdge) / 4));  
        const tier \= Math.abs(totalEdge) \>= 5.0 ? 'gold' : 'silver';

        bets.push({  
            type: 'total',  
            tier: tier,  
            gameId: game.id,  
            homeTeam: game.homeTeam,  
            awayTeam: game.awayTeam,  
            market: 'Total Points',  
            pick: pick,  
            line: game.total,  
            proj: sim.predictedTotal,  
            ev: parseFloat(ev.toFixed(1)),  
            units: parseFloat(units.toFixed(2)),  
            note: \`Model projects ${sim.predictedTotal.toFixed(1)} total points, line is ${game.total}.\`  
        });  
    }

    return bets;  
  }  
    
  // FIX: Implemented missing helper method '\_mapStat'.  
  private \_mapStat(p: Player, market: string): number | null {  
    if (\!p.projected) return null;  
    const proj \= p.projected;  
    const lowerMarket \= market.toLowerCase();

    if (lowerMarket.includes('points')) return proj.pts;  
    if (lowerMarket.includes('rebounds')) return proj.reb;  
    if (lowerMarket.includes('assists')) return proj.ast;  
    if (lowerMarket.includes('threes')) return proj.fg3m ?? 0;  
    if (lowerMarket.includes('steals')) return proj.stl ?? 0;  
    if (lowerMarket.includes('blocks')) return proj.blk ?? 0;  
    return null;  
  }

  // FIX: Implemented missing helper method '\_mapBaselineStat'.  
  private \_mapBaselineStat(p: Player, market: string): number | null {  
    const stats \= p.stats.l20;  
    const lowerMarket \= market.toLowerCase();

    if (lowerMarket.includes('points')) return stats.pts;  
    if (lowerMarket.includes('rebounds')) return stats.reb;  
    if (lowerMarket.includes('assists')) return stats.ast;  
    if (lowerMarket.includes('threes')) return stats.fg3m ?? 0;  
    if (lowerMarket.includes('steals')) return stats.stl;  
    if (lowerMarket.includes('blocks')) return stats.blk;  
    return null;  
  }

  private mapMarketToStat(market: string): string {  
    if (market.includes('points')) return 'PTS';  
    if (market.includes('rebounds')) return 'REB';  
    if (market.includes('assists')) return 'AST';  
    if (market.includes('threes')) return '3PT';  
    if (market.includes('steals')) return 'STL';  
    if (market.includes('blocks')) return 'BLK';  
    return market.replace('player\_', '').toUpperCase();  
  }  
}  
// \--- END OF FILE src/services/alchemist.service.ts \---

// \--- START OF FILE src/services/analytics.service.ts \---  
import { Injectable, inject } from '@angular/core';  
import { Player } from './model-data.service';  
import { GameLog } from '../data/history-data';  
import { HistoryService } from './history.service';

export interface ShotProfile {  
  rimPct: number;  
  midPct: number;  
  threePct: number;  
}

export interface TeamProfile {  
  pace: number;  
  shotProfile: ShotProfile;  
  threePointRate: number; // 3PA / FGA  
  freeThrowRate: number; // FTA / FGA  
}

export interface TeamSplits {  
  homeRecord: string;  
  awayRecord: string;  
  avgPtsForHome: string;  
  avgPtsAgainstHome: string;  
  avgPtsForAway: string;  
  avgPtsAgainstAway: string;  
}

@Injectable({  
  providedIn: 'root'  
})  
export class AnalyticsService {  
  private historyService \= inject(HistoryService);

  // Caching to avoid re-computing for the same teams  
  private teamProfileCache \= new Map\<string, { offensive: TeamProfile, defensive: TeamProfile }\>();  
  private splitsCache \= new Map\<string, TeamSplits\>();

  /\*\*  
   \* Main public method to get both profiles for a team.  
   \* Uses cache if available.  
   \*/  
  public getTeamProfiles(teamAbbr: string, roster: Player\[\]): { offensive: TeamProfile, defensive: TeamProfile } {  
    if (this.teamProfileCache.has(teamAbbr)) {  
      return this.teamProfileCache.get(teamAbbr)\!;  
    }

    const offensive \= this.calculateTeamOffensiveProfile(roster);  
    const defensive \= this.calculateTeamDefensiveProfile(teamAbbr);  
      
    const profiles \= { offensive, defensive };  
    this.teamProfileCache.set(teamAbbr, profiles);  
      
    return profiles;  
  }

  /\*\*  
   \* NEW: Calculates Home/Away splits for a team.  
   \*/  
  public calculateTeamSplits(teamAbbr: string): TeamSplits {  
    if (this.splitsCache.has(teamAbbr)) {  
        return this.splitsCache.get(teamAbbr)\!;  
    }  
      
    const gameIdToLogs \= this.historyService.getGameLogsMap();  
    const teamGameIds \= this.historyService.getTeamGameIdsMap().get(teamAbbr) || new Set();

    const splits \= {  
        homeWins: 0, homeLosses: 0, awayWins: 0, awayLosses: 0,  
        homePtsFor: 0, homePtsAgainst: 0, awayPtsFor: 0, awayPtsAgainst: 0,  
        homeCount: 0, awayCount: 0  
    };

    teamGameIds.forEach(gameId \=\> {  
        const gameLogs \= gameIdToLogs.get(gameId);  
        if (\!gameLogs || gameLogs.length \< 2\) return;

        const teamLogSample \= gameLogs.find(l \=\> l.TEAM\_ABBREVIATION \=== teamAbbr);  
        if (\!teamLogSample) return;

        const isHome \= \!teamLogSample.MATCHUP.includes('@');  
        const isWin \= teamLogSample.WL \=== 'W';

        const teamScore \= gameLogs.filter(l \=\> l.TEAM\_ABBREVIATION \=== teamAbbr).reduce((sum, p) \=\> sum \+ p.PTS, 0);  
        const oppScore \= gameLogs.filter(l \=\> l.TEAM\_ABBREVIATION \!== teamAbbr).reduce((sum, p) \=\> sum \+ p.PTS, 0);

        if (teamScore \=== 0 || oppScore \=== 0\) return; // Skip incomplete games

        if (isHome) {  
            splits.homeCount++;  
            if (isWin) splits.homeWins++; else splits.homeLosses++;  
            splits.homePtsFor \+= teamScore;  
            splits.homePtsAgainst \+= oppScore;  
        } else {  
            splits.awayCount++;  
            if (isWin) splits.awayWins++; else splits.awayLosses++;  
            splits.awayPtsFor \+= teamScore;  
            splits.awayPtsAgainst \+= oppScore;  
        }  
    });

    const result: TeamSplits \= {  
        homeRecord: \`${splits.homeWins}-${splits.homeLosses}\`,  
        awayRecord: \`${splits.awayWins}-${splits.awayLosses}\`,  
        avgPtsForHome: splits.homeCount \> 0 ? (splits.homePtsFor / splits.homeCount).toFixed(1) : 'N/A',  
        avgPtsAgainstHome: splits.homeCount \> 0 ? (splits.homePtsAgainst / splits.homeCount).toFixed(1) : 'N/A',  
        avgPtsForAway: splits.awayCount \> 0 ? (splits.awayPtsFor / splits.awayCount).toFixed(1) : 'N/A',  
        avgPtsAgainstAway: splits.awayCount \> 0 ? (splits.awayPtsAgainst / splits.awayCount).toFixed(1) : 'N/A',  
    };

    this.splitsCache.set(teamAbbr, result);  
    return result;  
  }

  /\*\*  
   \* Infers a team's offensive identity from its current roster's stats.  
   \*/  
  private calculateTeamOffensiveProfile(roster: Player\[\]): TeamProfile {  
    let totalFga \= 0, totalFg3a \= 0, totalFta \= 0, totalMin \= 0;  
    let weightedRimPct \= 0, weightedMidPct \= 0, weightedThreePct \= 0;

    const activeRoster \= roster.filter(p \=\> (p.stats.l20.min || 0\) \> 5);

    for (const player of activeRoster) {  
      const stats \= player.stats.l20;  
      const fga \= stats.fga || 0;  
      totalFga \+= fga;  
      totalFg3a \+= stats.fg3a || 0;  
      totalFta \+= stats.fta || 0;  
      totalMin \+= stats.min || 0;

      const playerProfile \= this.inferPlayerShotProfile(player);  
      weightedRimPct \+= playerProfile.rimPct \* fga;  
      weightedMidPct \+= playerProfile.midPct \* fga;  
      weightedThreePct \+= playerProfile.threePct \* fga;  
    }

    if (totalFga \=== 0\) return this.getEmptyProfile();

    // Pace: Possessions per 48 minutes. FGA is a decent proxy.  
    const pace \= totalMin \> 0 ? (totalFga / totalMin) \* 48 : 98.0;

    return {  
      pace: parseFloat(pace.toFixed(1)),  
      shotProfile: {  
        rimPct: parseFloat(((weightedRimPct / totalFga) \* 100).toFixed(1)),  
        midPct: parseFloat(((weightedMidPct / totalFga) \* 100).toFixed(1)),  
        threePct: parseFloat(((weightedThreePct / totalFga) \* 100).toFixed(1)),  
      },  
      threePointRate: parseFloat(((totalFg3a / totalFga) \* 100).toFixed(1)),  
      freeThrowRate: parseFloat(((totalFta / totalFga) \* 100).toFixed(1)),  
    };  
  }

  /\*\*  
   \* Infers a team's defensive vulnerabilities by analyzing how their opponents perform against them.  
   \*/  
  private calculateTeamDefensiveProfile(teamAbbr: string): TeamProfile {  
    const opponentLogs: GameLog\[\] \= \[\];  
    const teamGameIds \= this.historyService.getTeamGameIdsMap().get(teamAbbr) || new Set();  
    const gameLogsMap \= this.historyService.getGameLogsMap();

    teamGameIds.forEach(gameId \=\> {  
      const gameLogs \= gameLogsMap.get(gameId);  
      if (gameLogs) {  
        for (const log of gameLogs) {  
          if (log.TEAM\_ABBREVIATION \!== teamAbbr) {  
            opponentLogs.push(log);  
          }  
        }  
      }  
    });  
      
    if (opponentLogs.length \=== 0\) return this.getEmptyProfile();

    // Aggregate stats from all opponents  
    const aggregated \= opponentLogs.reduce((acc, log) \=\> {  
        acc.fga \+= log.FGA;  
        acc.fg3a \+= log.FG3A;  
        acc.fta \+= log.FTA;  
        acc.min \+= log.MIN;  
        return acc;  
    }, { fga: 0, fg3a: 0, fta: 0, min: 0 });

    if (aggregated.fga \=== 0\) return this.getEmptyProfile();

    // Pace is determined by both teams, so we use the game minutes  
    const totalMinutesForAllGames \= aggregated.min / 5; // Min is for all players, approx 5 per team on court  
    const pace \= totalMinutesForAllGames \> 0 ? (aggregated.fga / totalMinutesForAllGames) \* 48 : 98.0;

    // What percentage of shots against this D are threes?  
    const threePointRate \= (aggregated.fg3a / aggregated.fga) \* 100;

    // How often do opponents get to the line against this D?  
    const freeThrowRate \= (aggregated.fta / aggregated.fga) \* 100;

    // For shot profile against, we can't infer rim/mid as easily without player data.  
    // We'll use 3P rate and a proxy for interior defense (FTA rate).  
    const rimAllowed \= Math.min(60, freeThrowRate \* 1.5); // Heuristic: high fouls \= more shots at rim  
    const threeAllowed \= threePointRate;  
    const midAllowed \= 100 \- rimAllowed \- threeAllowed;

    return {  
      pace: parseFloat(pace.toFixed(1)),  
      shotProfile: {  
        rimPct: parseFloat(rimAllowed.toFixed(1)),  
        midPct: parseFloat(Math.max(0, midAllowed).toFixed(1)),  
        threePct: parseFloat(threeAllowed.toFixed(1)),  
      },  
      threePointRate: parseFloat(threePointRate.toFixed(1)),  
      freeThrowRate: parseFloat(freeThrowRate.toFixed(1)),  
    };  
  }

  /\*\*  
   \* Infers a single player's shot distribution based on their box score stats.  
   \* This is a heuristic model.  
   \*/  
  private inferPlayerShotProfile(player: Player): ShotProfile {  
    const stats \= player.stats.l20;  
    const pos \= player.position;  
    const totalFga \= stats.fga || 1; // Avoid division by zero  
      
    if (totalFga \=== 0\) return { rimPct: 0, midPct: 0, threePct: 0 };

    // 1\. 3-pointers are known directly  
    const threeAttempts \= stats.fg3a || 0;

    // 2\. Infer At-Rim attempts (heuristic)  
    // Players who shoot at the rim get fouled more.  
    const ftaFactor \= (stats.fta || 0\) \* 0.4;  
    // Positional prior: Bigs shoot more at the rim.  
    const posFactor \= (pos.includes('C') || pos.includes('F')) ? 0.3 : 0.15;  
    // Efficiency: High 2P% suggests shots are closer.  
    const twoPtAttempts \= totalFga \- threeAttempts;  
    const twoPtMakes \= (stats.fgm || 0\) \- (stats.fg3m || 0);  
    const twoPtPct \= twoPtAttempts \> 0 ? twoPtMakes / twoPtAttempts : 0;  
    const effFactor \= twoPtPct \> 0.5 ? (twoPtPct \- 0.5) \* twoPtAttempts \* 0.5 : 0;  
      
    const rimAttempts \= Math.min(twoPtAttempts, ftaFactor \+ (twoPtAttempts \* posFactor) \+ effFactor);

    // 3\. Mid-range are what's left over  
    const midAttempts \= totalFga \- threeAttempts \- rimAttempts;

    return {  
      rimPct: Math.max(0, rimAttempts / totalFga),  
      midPct: Math.max(0, midAttempts / totalFga),  
      threePct: Math.max(0, threeAttempts / totalFga),  
    };  
  }  
    
  private getEmptyProfile(): TeamProfile {  
      return {  
          pace: 98.0,  
          shotProfile: { rimPct: 33, midPct: 34, threePct: 33 },  
          threePointRate: 33.0,  
          freeThrowRate: 25.0,  
      };  
  }  
}  
// \--- END OF FILE src/services/analytics.service.ts \---

// \--- START OF FILE src/services/calibrator.service.ts \---  
import { Injectable, inject } from '@angular/core';  
import { Player } from './model-data.service';  
import { PlayTypeService } from './play-type.service';

export interface CalibrationContext {  
  opponent: string;  
  spread: number;  
  total: number;  
}

@Injectable({  
  providedIn: 'root'  
})  
export class CalibratorService {  
  private playTypeService \= inject(PlayTypeService);  
    
  // 1\. ADJUSTMENT CONSTANTS (MERGED FROM MODULE E & EXISTING LOGIC)  
  private readonly RULES \= {  
    MINUTES\_LIMIT: 0.75,  
    OUT: 0.0,  
    QUESTIONABLE\_FACTOR: 0.65, // Retained: Critical for risk management  
    DOUBTFUL\_FACTOR: 0.25,     // Retained: Critical for risk management  
    BLOWOUT\_RISK\_THRESHOLD: 12.5,  
    BLOWOUT\_FACTOR: 0.94,  
    HIGH\_TOTAL\_THRESHOLD: 238.0,  
    LOW\_TOTAL\_THRESHOLD: 218.0,  
    HIGH\_TOTAL\_FACTOR: 1.03,  
    LOW\_TOTAL\_FACTOR: 0.97,  
  };

  // 2\. DEFENSIVE SCHEMES (FROM MODULE E \- 2025-26 V5.6)  
  private readonly DEFENSIVE\_STYLES: Record\<string, string\> \= {  
    // THE ELITE WALLS (Paint Pack / Elite Interior)  
    "OKC": "PAINT\_PACK", "BOS": "PAINT\_PACK", "DET": "PAINT\_PACK",   
    "MIN": "PAINT\_PACK", "SAS": "PAINT\_PACK", "ORL": "PAINT\_PACK",  
      
    // HIGH PRESSURE / TURNOVER GENERATORS (Blitz)  
    "HOU": "BLITZ", "TOR": "BLITZ", "MIA": "BLITZ", "PHO": "BLITZ",  
      
    // SWITCH-HEAVY / PERIMETER FOCUS (Small Ball / Perimeter)  
    "GSW": "PERIMETER", "DAL": "PERIMETER", "NYK": "PERIMETER",  
      
    // VOLUMETRIC VULNERABILITY (Funnel / High Pace)  
    "WAS": "FUNNEL", "ATL": "FUNNEL", "CHI": "FUNNEL", "UTA": "FUNNEL", "SAC": "FUNNEL",  
      
    // FOUL-PRONE / PHYSICAL (Hackers)  
    "IND": "HACKERS", "CHA": "HACKERS", "POR": "HACKERS"  
  };

  getDefensiveStyle(teamAbbr: string): string {  
    return this.DEFENSIVE\_STYLES\[teamAbbr\] || 'NEUTRAL';  
  }

  /\*\*  
   \* Main Calibration Routine (V5.6 Logic)  
   \*/  
  calibratePlayer(player: Player, context: CalibrationContext): Player {  
    const p \= JSON.parse(JSON.stringify(player)); // Deep copy  
    if (\!p.calibrationNotes) p.calibrationNotes \= '';  
      
    // 1\. ASSIGN PLAY TYPE (New, more granular system)  
    p.primaryPlayType \= this.playTypeService.assignPlayType(p);

    // 2\. STATUS CALIBRATION  
    if (p.isOut || p.status \=== 'Out') {  
        this.zeroOut(p);  
        p.calibrationNotes \= 'Official OUT';  
        return p;  
    }  
      
    if (p.status \=== 'Minutes Limit') {  
        this.applyFactor(p, this.RULES.MINUTES\_LIMIT);  
        p.calibrationNotes \+= ' | Limit Applied';  
    }  
    if (p.status \=== 'Questionable') {  
        this.applyFactor(p, this.RULES.QUESTIONABLE\_FACTOR);  
        p.calibrationNotes \+= ' | Questionable Risk';  
    }  
    if (p.status \=== 'Doubtful') {  
        this.applyFactor(p, this.RULES.DOUBTFUL\_FACTOR);  
        p.calibrationNotes \+= ' | Doubtful Risk';  
    }

    // 3\. GAME SCRIPT  
    const spreadAbs \= Math.abs(context.spread);  
    const baseMin \= p.stats.l20.min || 0;

    if (spreadAbs \> this.RULES.BLOWOUT\_RISK\_THRESHOLD && baseMin \> 30.0) {  
        this.applyFactor(p, this.RULES.BLOWOUT\_FACTOR);  
        p.calibrationNotes \+= \` | Blowout Risk (${spreadAbs})\`;  
    }

    if (context.total \> this.RULES.HIGH\_TOTAL\_THRESHOLD) {  
        this.applyFactor(p, this.RULES.HIGH\_TOTAL\_FACTOR);  
        p.calibrationNotes \+= ' | High Octane';  
    } else if (context.total \> 0 && context.total \< this.RULES.LOW\_TOTAL\_THRESHOLD) {  
        this.applyFactor(p, this.RULES.LOW\_TOTAL\_FACTOR);  
        p.calibrationNotes \+= ' | Grind Game';  
    }

    // 4\. ADVANCED MATCHUP LOGIC (Play Type vs Defensive Scheme)  
    const defStyle \= this.DEFENSIVE\_STYLES\[context.opponent\] || 'NEUTRAL';  
      
    if (p.primaryPlayType \=== 'PNR\_BALL\_HANDLER' && defStyle \=== 'BLITZ') {  
        this.boostStat(p, 'ast', 1.10); // More passing out of traps  
        this.boostStat(p, 'tov', 1.20); // Higher turnover risk  
        this.boostStat(p, 'pts', 0.95); // Scoring is tougher  
        p.calibrationNotes \+= \` | vs Blitz (Pass-First)\`;  
    }  
    else if (p.primaryPlayType \=== 'SPOT\_UP\_SHOOTER' && defStyle \=== 'PAINT\_PACK') {  
        this.boostStat(p, 'fg3m', 1.15); // Shooters eat against drop coverage  
        this.boostStat(p, 'fg3a', 1.15);  
        p.calibrationNotes \+= \` | vs Paint Pack (Open Looks)\`;  
    }  
    else if (p.primaryPlayType \=== 'ISOLATION\_SCORER' && defStyle \=== 'PERIMETER') {  
        this.boostStat(p, 'pts', 0.93); // Harder to score on a switch-heavy scheme  
        this.boostStat(p, 'fga', 0.95);  
        p.calibrationNotes \+= \` | vs Perimeter D (Tough ISO)\`;  
    }  
    else if (p.primaryPlayType \=== 'PNR\_ROLL\_MAN' && defStyle \=== 'PERIMETER') {  
        this.boostStat(p, 'oreb', 1.25); // Size advantage on the glass  
        this.boostStat(p, 'reb', 1.10);  
        p.calibrationNotes \+= \` | vs Perimeter D (Size Advantage)\`;  
    }  
    else if (p.primaryPlayType \=== 'TRANSITION\_ACE' && defStyle \=== 'FUNNEL') {  
        this.boostStat(p, 'pts', 1.05); // More fast break points in high-pace games  
        p.calibrationNotes \+= \` | vs Funnel D (High Pace)\`;  
    }  
      
    // Clean up notes  
    p.calibrationNotes \= p.calibrationNotes.replace(/^ \\| /, '');

    return p;  
  }

  private applyFactor(p: Player, factor: number) {  
    if (\!p.projected) return;  
    const proj \= p.projected;  
    const keys: (keyof typeof proj)\[\] \= \['pts', 'reb', 'ast', 'min', 'fga', 'fg3m', 'fta', 'oreb', 'dreb', 'fg3a', 'tov', 'stl', 'blk'\];  
    keys.forEach(k \=\> {  
      if (proj\[k\] \!== undefined && typeof proj\[k\] \=== 'number') {  
          (proj as any)\[k\] \= parseFloat(((proj\[k\] as number) \* factor).toFixed(2));  
      }  
    });  
  }

  private boostStat(p: Player, stat: keyof Player\['projected'\], factor: number) {  
     if (\!p.projected) return;  
     const proj \= p.projected;  
     if (proj\[stat\] \!== undefined && typeof proj\[stat\] \=== 'number') {  
         (proj as any)\[stat\]\! \= parseFloat(((proj as any)\[stat\]\! \* factor).toFixed(2));  
     }  
  }

  private zeroOut(p: Player) {  
      if (\!p.projected) return;  
      Object.keys(p.projected).forEach(k \=\> {  
          (p.projected as any)\[k\] \= 0;  
      });  
  }  
}  
// \--- END OF FILE src/services/calibrator.service.ts \---

// \--- START OF FILE src/services/config.service.ts \---  
import { Injectable, signal } from '@angular/core';

@Injectable({  
  providedIn: 'root'  
})  
export class ConfigService {  
  // \====================================================  
  // 1\. ODDS & LINES PROVIDERS  
  // \====================================================  
  // PRIMARY FOR GAME LINES (Spreads, Totals, Moneyline)  
  readonly oddsApiKey \= '3c4cff00b16889e49fc6320ffb0690a8';  
    
  // PRIMARY FOR PLAYER PROPS (Source 1\)  
  readonly sgoApiKey \= '8d04b4a7503bf43f87c9db88e8b53dd8';

  // \====================================================  
  // 2\. DATA & STATS PROVIDERS  
  // \====================================================  
  // LIVE STATS & ROSTERS (Tank01)  
  readonly tank01Key \= 'b4ec1031f4msh80f4fc4cd874de4p17e5b7jsn8eeafd9da310';

  // \====================================================  
  // 3\. NEWS & SCOUTING (The Yak)  
  // \====================================================  
  readonly googleSearchKey \= 'AIzaSyAly9xlQ6of5WLmHDyzGORokvcbc7cg-nA';  
  readonly googleSearchCx \= '435db9cf0319e43db';

  // \====================================================  
  // 4\. ALERTS & REPORTING  
  // \====================================================  
  readonly telegramToken \= '8190581794:AAEUVV88PupubJYcudiyRCuWCpgPVLlZ-ag';  
  // IMPORTANT: Get your ID from @userinfobot on Telegram. A bot cannot message itself.  
  readonly telegramChatId \= '8200754019';

  // \====================================================  
  // 5\. GLOBAL SETTINGS  
  // \====================================================  
    
  // Exact match to config.py: CURRENT\_SEASON \= "2025-2026"  
  readonly currentSeason \= signal('2025-2026');  
    
  readonly refreshHours \= signal(6);  
  readonly brandHeader \= signal('ludi informatio'); 

  // Feature Flags  
  readonly enableTelegramAlerts \= signal(true);  
  readonly runSeasonInit \= signal(false);

  // \====================================================  
  // 6\. DFS & PROP SETTINGS (THE UNLOCK)  
  // \====================================================  
  readonly toaDfsRegion \= 'us\_dfs';  
  readonly toaMarkets \= 'player\_points,player\_rebounds,player\_assists';  
    
  readonly sgoDfsBooks \= 'prizepicks,underdog,dabble';  
  readonly sgoIncludeAlts \= signal(true);  
}  
// \--- END OF FILE src/services/config.service.ts \---

// \--- START OF FILE src/services/history.service.ts \---  
import { Injectable, signal, computed } from '@angular/core';  
import { GameLog, HISTORY\_DATA } from '../data/history-data';

@Injectable({  
  providedIn: 'root'  
})  
export class HistoryService {  
  // The in-memory database (Pandas DataFrame equivalent)  
  readonly db \= signal\<GameLog\[\]\>(\[\]);

  // NEW: Converted from computed signals to standard properties for performance.  
  // They are now populated only when the DB is written to.  
  private playerLogsMap: Map\<string, GameLog\[\]\> \= new Map();  
  private gameLogsMap: Map\<string, GameLog\[\]\> \= new Map();  
  private teamGameIdsMap: Map\<string, Set\<string\>\> \= new Map();

  readonly dbStatus \= computed(() \=\> {  
    const logs \= this.db();  
    if (logs.length \=== 0\) {  
      return 'DB: Empty';  
    }  
    const lastDate \= this.getLastDate();  
    const dateStr \= lastDate ? lastDate.toISOString().split('T')\[0\] : 'N/A';  
    return \`DB: ${logs.length.toLocaleString()} rows | Last: ${dateStr}\`;  
  });  
    
  /\*\*  
   \* Loads the STATIC fallback data into the DB.  
   \*/  
  loadFallbackDatabase(): number {  
    console.warn('\[HISTORY\] Loading fallback static data.');  
    const data \= HISTORY\_DATA;  
    this.db.set(data);  
    this.\_rebuildMaps(data); // Rebuild maps on new data  
    return data.length;  
  }

  /\*\*  
   \* Adds new logs fetched from the API to the in-memory database.  
   \*/  
  mergeLogs(newLogs: GameLog\[\]) {  
    if (newLogs.length \=== 0\) return;  
    const combined \= \[...this.db(), ...newLogs\];  
    this.db.set(combined);  
    this.\_rebuildMaps(combined); // Rebuild maps on new data  
  }

  // Helper to rebuild all maps from a fresh dataset  
  private \_rebuildMaps(logs: GameLog\[\]) {  
      this.playerLogsMap.clear();  
      this.gameLogsMap.clear();  
      this.teamGameIdsMap.clear();

      for (const log of logs) {  
        // Player Logs Map  
        if (\!this.playerLogsMap.has(log.PLAYER\_NAME)) {  
          this.playerLogsMap.set(log.PLAYER\_NAME, \[\]);  
        }  
        this.playerLogsMap.get(log.PLAYER\_NAME)\!.push(log);

        // Game Logs Map  
        if (\!this.gameLogsMap.has(log.GAME\_ID)) {  
          this.gameLogsMap.set(log.GAME\_ID, \[\]);  
        }  
        this.gameLogsMap.get(log.GAME\_ID)\!.push(log);

        // Team Game IDs Map  
        if (\!this.teamGameIdsMap.has(log.TEAM\_ABBREVIATION)) {  
          this.teamGameIdsMap.set(log.TEAM\_ABBREVIATION, new Set());  
        }  
        this.teamGameIdsMap.get(log.TEAM\_ABBREVIATION)\!.add(log.GAME\_ID);  
      }

      // Sort logs for each player once after mapping  
      for (const playerLogs of this.playerLogsMap.values()) {  
        playerLogs.sort((a, b) \=\> new Date(b.GAME\_DATE).getTime() \- new Date(a.GAME\_DATE).getTime());  
      }  
  }

  // \--- PUBLIC GETTERS FOR MAPS \---  
  public getPlayerLogsMap(): Map\<string, GameLog\[\]\> { return this.playerLogsMap; }  
  public getGameLogsMap(): Map\<string, GameLog\[\]\> { return this.gameLogsMap; }  
  public getTeamGameIdsMap(): Map\<string, Set\<string\>\> { return this.teamGameIdsMap; }

  /\*\*  
   \* Returns the date of the most recent game in the DB.  
   \*/  
  getLastDate(): Date | null {  
    const data \= this.db();  
    if (data.length \=== 0\) return null;

    const sorted \= \[...data\].sort((a, b) \=\>   
      new Date(b.GAME\_DATE).getTime() \- new Date(a.GAME\_DATE).getTime()  
    );  
      
    return new Date(sorted\[0\].GAME\_DATE);  
  }

  /\*\*  
   \* Get raw logs for a specific player (now uses fast cache).  
   \*/  
  getPlayerHistory(playerName: string): GameLog\[\] {  
    return this.playerLogsMap.get(playerName) || \[\];  
  }

  /\*\*  
   \* Get all logs for a team (Undeduplicated).  
   \*/  
  getTeamLogs(teamAbbr: string): GameLog\[\] {  
    return this.db().filter(log \=\> log.TEAM\_ABBREVIATION \=== teamAbbr);  
  }

  /\*\*  
   \* Get team history.  
   \*/  
  getUniqueTeamGames(teamAbbr: string): GameLog\[\] {  
    const rawLogs \= this.getTeamLogs(teamAbbr);  
    const seenGames \= new Set\<string\>();  
    const uniqueGames: GameLog\[\] \= \[\];

    for (const log of rawLogs) {  
      if (\!seenGames.has(log.GAME\_ID)) {  
        seenGames.add(log.GAME\_ID);  
        uniqueGames.push(log);  
      }  
    }  
      
    return uniqueGames.sort((a, b) \=\> new Date(b.GAME\_DATE).getTime() \- new Date(a.GAME\_DATE).getTime());  
  }

  /\*\*  
   \* Get last N games for a team (Deduplicated)  
   \*/  
  getLastNGames(teamAbbr: string, n: number): GameLog\[\] {  
    return this.getUniqueTeamGames(teamAbbr).slice(0, n);  
  }

  /\*\*  
   \* Logic ported from Module 2 (initialize\_season.py)  
   \*/  
  determineCurrentNBASeason(): string {  
    const now \= new Date();  
    const month \= now.getMonth() \+ 1; // 1-12  
    const year \= now.getFullYear();

    let startYear \= year;  
    let endYear \= year \+ 1;

    if (month \< 10\) {  
      startYear \= year \- 1;  
      endYear \= year;  
    }

    return \`${startYear}-${String(endYear).slice(-2)}\`;  
  }  
}  
// \--- END OF FILE src/services/history.service.ts \---

// \--- START OF FILE src/services/historian.service.ts \---  
import { Injectable, inject } from '@angular/core';  
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';  
import { lastValueFrom } from 'rxjs';  
import { ConfigService } from './config.service';  
import { HistoryService } from './history.service';  
import { GameLog } from '../data/history-data';

@Injectable({  
  providedIn: 'root'  
})  
export class HistorianService {  
  // FIX: Explicitly type injected HttpClient to resolve type inference issue.  
  private http: HttpClient \= inject(HttpClient);  
  private config \= inject(ConfigService);  
  private history \= inject(HistoryService);

  private readonly TANK\_HOST \= 'tank01-fantasy-stats.p.rapidapi.com';

  // Tank01 often uses non-standard abbreviations compared to OddsAPI  
  // This map normalizes them so the "Join" in ModelDataService works reliably.  
  private readonly TANK\_MAP: Record\<string, string\> \= {  
    'GS': 'GSW',  
    'PHO': 'PHX',  
    'NO': 'NOP',  
    'SA': 'SAS',  
    'NY': 'NYK',  
    'WSH': 'WAS',  
    'UTAH': 'UTA',  
    'BKN': 'BKN',   
    'CHA': 'CHA'  
  };

  /\*\*  
   \* NEW: Fetches all game logs for the entire current season.  
   \* This simulates the initial database creation from \`initialize\_season.py\`.  
   \*/  
  async fetchFullSeasonHistory(): Promise\<GameLog\[\]\> {  
    console.log(\`\[HISTORIAN\] 🚀 Beginning full season data fetch...\`);  
    const seasonStr \= this.config.currentSeason();  
    const startYear \= parseInt(seasonStr.split('-')\[0\], 10);  
      
    // NBA seasons typically start in mid-October.  
    let currentDate \= new Date(\`${startYear}-10-15T12:00:00Z\`);  
    const today \= new Date();  
      
    // Don't fetch future data.  
    if (currentDate \> today) {  
        console.log(\`\[HISTORIAN\] Season start date (${currentDate.toISOString().split('T')\[0\]}) is in the future. Fetch aborted.\`);  
        return \[\];  
    }

    let allLogs: GameLog\[\] \= \[\];  
    let daysFetched \= 0;

    while (currentDate \<= today) {  
      const dateStrApi \= this.formatDateForApi(currentDate);  
      const dateIso \= currentDate.toISOString().split('T')\[0\];

      try {  
        const dailyLogs \= await this.fetchTank01Boxscores(dateStrApi, dateIso);  
        if (dailyLogs.length \> 0\) {  
          allLogs \= \[...allLogs, ...dailyLogs\];  
          console.log(\`\[HISTORIAN\]   \> Fetched ${dailyLogs.length} records for ${dateIso}\`);  
        }  
      } catch (e) {  
        console.error(\`\[HISTORIAN\] ❌ Failed to fetch logs for ${dateIso}\`, e);  
      }

      // Move to the next day  
      currentDate.setDate(currentDate.getDate() \+ 1);  
      daysFetched++;  
        
      // Safety break to avoid infinite loops or excessive API calls during development  
      if (daysFetched \> 200\) { // Approx a full season length \+ playoffs  
          console.warn("\[HISTORIAN\] Safety break triggered after 200 days.");  
          break;  
      }  
        
      // Small delay to be kind to the API  
      await new Promise(r \=\> setTimeout(r, 50));   
    }  
      
    console.log(\`\[HISTORIAN\] ✅ Full season fetch complete. Total records: ${allLogs.length}\`);  
    return allLogs;  
  }

  /\*\*  
   \* Main Routine: Checks last update date, fetches missing days from Tank01,  
   \* and appends new rows to the in-memory database.  
   \*/  
  async syncDatabase(): Promise\<string\> {  
    const lastDate \= this.history.getLastDate();  
      
    if (\!lastDate) {  
      return '⚠️ Database empty. Initial load required.';  
    }

    const today \= new Date();  
    today.setHours(0, 0, 0, 0);  
      
    const diffTime \= Math.abs(today.getTime() \- lastDate.getTime());  
    const diffDays \= Math.ceil(diffTime / (1000 \* 60 \* 60 \* 24));

    if (diffDays \<= 1\) {  
      return \`✅ Database up to date. (Last: ${lastDate.toISOString().split('T')\[0\]})\`;  
    }

    console.log(\`\[HISTORIAN\] 🔄 Fetching missing games for ${diffDays} days...\`);

    let newRecords: GameLog\[\] \= \[\];  
    let checkDate \= new Date(lastDate);  
    checkDate.setDate(checkDate.getDate() \+ 1);

    while (checkDate \< today) {  
      const dateStr \= this.formatDateForApi(checkDate);  
      const dateIso \= checkDate.toISOString().split('T')\[0\];  
        
      console.log(\`\[HISTORIAN\] \> Checking Date: ${dateIso}...\`);  
        
      try {  
        const dailyStats \= await this.fetchTank01Boxscores(dateStr, dateIso);  
        if (dailyStats.length \> 0\) {  
          newRecords \= \[...newRecords, ...dailyStats\];  
        }  
      } catch (e) {  
        console.error(\`\[HISTORIAN\] Failed to fetch ${dateIso}\`, e);  
      }

      checkDate.setDate(checkDate.getDate() \+ 1);  
      if (newRecords.length \> 500\) break;   
    }

    if (newRecords.length \> 0\) {  
      this.history.mergeLogs(newRecords);  
      return \`💾 SUCCESS: Added ${newRecords.length} new rows.\`;  
    }

    return 'ℹ️ No new data found.';  
  }

  /\*\*  
   \* LIVE DATA: Get the schedule for a specific date (Defaults to Today).  
   \*/  
  async fetchDailySchedule(date: Date): Promise\<any\[\]\> {  
    const dateStr \= this.formatDateForApi(date);  
    const headers \= new HttpHeaders({  
      'X-RapidAPI-Key': this.config.tank01Key,  
      'X-RapidAPI-Host': this.TANK\_HOST  
    });

    const params \= new HttpParams().set('gameDate', dateStr);

    try {  
      console.log(\`\[HISTORIAN\] Fetching schedule for ${dateStr}...\`);  
      const response: any \= await lastValueFrom(  
        this.http.get(\`https://${this.TANK\_HOST}/getNBAGamesForDate\`, { headers, params })  
      );  
      return response.body || \[\];  
    } catch (e) {  
      console.warn('Failed to fetch daily schedule', e);  
      return \[\];  
    }  
  }

  /\*\*  
   \* PUBLIC API: Get Box Score/Roster for a specific Game.  
   \* Connects ModelDataService to Tank01.  
   \*/  
  async getGameBoxScore(tankGameId: string, dateIso: string): Promise\<GameLog\[\]\> {  
     const headers \= new HttpHeaders({  
      'X-RapidAPI-Key': this.config.tank01Key,  
      'X-RapidAPI-Host': this.TANK\_HOST  
    });  
    return this.fetchSingleGameBox(tankGameId, dateIso, headers);  
  }

  /\*\*  
   \* SIMULATION: Get a pre-canned box score from static data to simulate a finished game.  
   \*/  
  getSimulatedBoxScore(mockGameId: string, homeTeam: string, awayTeam: string): GameLog\[\] {  
    // For this simulation, we'll use a specific game from our history to serve as the box score.  
    // The LAL @ GSW game from 2025-11-10 is game '0022500130' in history-data.ts  
    const targetGameId \= '0022500130';   
    if (mockGameId \=== 'mock\_1\_lal\_gsw') {  
      return this.history.db().filter(log \=\> log.GAME\_ID \=== targetGameId);  
    }  
    // Return empty for other mock games so they fall back to prop-based rosters  
    return \[\];  
  }

  /\*\*  
   \* HELPER: Find Tank01 GameID by matching teams.  
   \* Normalized to handle 'GS' vs 'GSW' discrepancies.  
   \*/  
  async findTankGameId(date: Date, homeTeam: string, awayTeam: string): Promise\<string | null\> {  
    const schedule \= await this.fetchDailySchedule(date);  
      
    const match \= schedule.find((g: any) \=\> {  
      // Tank01 keys might be 'home', 'homeTeam', 'hTeam' etc. usually 'home'  
      const tHome \= this.normalizeTankTeam(g.home || g.homeTeam);  
      const tAway \= this.normalizeTankTeam(g.away || g.awayTeam);  
        
      return tHome \=== homeTeam && tAway \=== awayTeam;  
    });

    return match ? match.gameID : null;  
  }

  // \--- INTERNAL HELPERS \---

  private normalizeTankTeam(raw: string): string {  
    if (\!raw) return '';  
    const upper \= raw.toUpperCase();  
    return this.TANK\_MAP\[upper\] || upper;  
  }

  private async fetchTank01Boxscores(dateStrApi: string, dateIso: string): Promise\<GameLog\[\]\> {  
    const headers \= new HttpHeaders({  
      'X-RapidAPI-Key': this.config.tank01Key,  
      'X-RapidAPI-Host': this.TANK\_HOST  
    });

    const params \= new HttpParams().set('gameDate', dateStrApi);

    try {  
      const response: any \= await lastValueFrom(  
        this.http.get(\`https://${this.TANK\_HOST}/getNBAGamesForDate\`, { headers, params })  
      );

      const games \= response.body || \[\];  
      if (\!Array.isArray(games) || games.length \=== 0\) return \[\];

      let cleanStats: GameLog\[\] \= \[\];

      for (const game of games) {  
        const gameId \= game.gameID;  
        if (gameId) {  
          const gameStats \= await this.fetchSingleGameBox(gameId, dateIso, headers);  
          cleanStats \= \[...cleanStats, ...gameStats\];  
        }  
      }

      return cleanStats;  
    } catch (e) {  
      console.warn('Tank01 API Request failed', e);  
      return \[\];  
    }  
  }

  private async fetchSingleGameBox(gameId: string, dateIso: string, headers: HttpHeaders): Promise\<GameLog\[\]\> {  
    const params \= new HttpParams()  
      .set('gameID', gameId)  
      .set('fantasyPoints', 'false');

    try {  
      const response: any \= await lastValueFrom(  
        this.http.get(\`https://${this.TANK\_HOST}/getNBABoxScore\`, { headers, params })  
      );

      const body \= response.body || {};  
      const playerStats \= body.playerStats || {};  
      const results: GameLog\[\] \= \[\];

      for (const \[pId, stats\] of Object.entries(playerStats) as \[string, any\]) {  
        const record: GameLog \= {  
          GAME\_DATE: dateIso,  
          SEASON\_ID: this.config.currentSeason(),  
          PLAYER\_ID: parseInt(pId, 10),  
          PLAYER\_NAME: stats.longName || 'Unknown',  
          TEAM\_ID: 0,  
          TEAM\_ABBREVIATION: stats.teamAbv || 'UNK',  
          TEAM\_NAME: '',  
          GAME\_ID: gameId,  
          MATCHUP: '',  
          WL: '',  
          PTS: Number(stats.pts || 0),  
          AST: Number(stats.ast || 0),  
          REB: Number(stats.reb || 0),  
          MIN: this.cleanMinutes(stats.mins),  
          STL: Number(stats.stl || 0),  
          BLK: Number(stats.blk || 0),  
          TOV: Number(stats.TOV || stats.to || 0),  
          PF: Number(stats.pf || 0),  
          FGM: Number(stats.fgm || 0),  
          FGA: Number(stats.fga || 0),  
          FG\_PCT: 0,  
          FG3M: Number(stats.tptfgm || 0),  
          FG3A: Number(stats.tptfga || 0),  
          FG3\_PCT: 0,  
          FTM: Number(stats.ftm || 0),  
          FTA: Number(stats.fta || 0),  
          FT\_PCT: 0,  
          OREB: Number(stats.oreb || 0),  
          DREB: Number(stats.dreb || 0),  
          PLUS\_MINUS: 0,  
          FANTASY\_PTS: 0,  
          VIDEO\_AVAILABLE: 0  
        };

        results.push(record);  
      }  
      return results;

    } catch (e) {  
      return \[\];  
    }  
  }

  private cleanMinutes(minVal: any): number {  
    if (\!minVal) return 0.0;  
    if (typeof minVal \=== 'number') return minVal;  
    if (typeof minVal \=== 'string' && minVal.includes(':')) {  
      try {  
        const parts \= minVal.split(':');  
        return parseInt(parts\[0\], 10\) \+ (parseInt(parts\[1\], 10\) / 60.0);  
      } catch {  
        return 0.0;  
      }  
    }  
    const parsed \= parseFloat(minVal);  
    return isNaN(parsed) ? 0.0 : parsed;  
  }

  private formatDateForApi(date: Date): string {  
    const yyyy \= date.getFullYear();  
    const mm \= String(date.getMonth() \+ 1).padStart(2, '0');  
    const dd \= String(date.getDate()).padStart(2, '0');  
    return \`${yyyy}${mm}${dd}\`;  
  }  
}  
// \--- END OF FILE src/services/historian.service.ts \---

// \--- START OF FILE src/services/lens-state.service.ts \---  
import { Injectable, signal } from '@angular/core';  
import { GameModel } from './model-data.service';

@Injectable({  
  providedIn: 'root'  
})  
export class LensStateService {  
  showLens \= signal(false);  
  gameContext \= signal\<GameModel | null\>(null);

  open(game: GameModel | null) {  
    this.gameContext.set(game);  
    this.showLens.set(true);  
  }

  close() {  
    this.showLens.set(false);  
    this.gameContext.set(null); // Clear context on close  
  }  
}  
// \--- END OF FILE src/services/lens-state.service.ts \---

// \--- START OF FILE src/services/lens.service.ts \---  
import { Injectable, inject } from '@angular/core';  
import { GoogleGenAI, Type } from '@google/genai';  
import { GameModel, Player } from './model-data.service';  
import { HistoryService } from './history.service';  
import { GameLog } from '../data/history-data';  
import { AnalyticsService } from './analytics.service';  
import { PlayTypeService } from './play-type.service';

export interface AiResponse {  
  summary: string;  
  chartData: any | null; // This will hold Chart.js config  
}

export interface Message {  
  author: 'user' | 'ai';  
  content: string;  
  chartData?: any | null;  
}

@Injectable({  
  providedIn: 'root'  
})  
export class LensService {  
  private historyService \= inject(HistoryService);  
  private analyticsService \= inject(AnalyticsService);  
  private playTypeService \= inject(PlayTypeService);

  async ask(query: string, gameContext: GameModel | null, allPlayers: Player\[\]): Promise\<AiResponse\> {  
    const apiKey \= process.env.API\_KEY;  
    if (\!apiKey) {  
      return { summary: "Error: API key is not configured.", chartData: null };  
    }

    const ai \= new GoogleGenAI({ apiKey });  
    const relevantData \= this.gatherContextualData(query, gameContext, allPlayers);  
    const prompt \= this.constructPrompt(query, gameContext, relevantData);

    const responseSchema \= {  
      type: Type.OBJECT,  
      properties: {  
        summary: { type: Type.STRING, description: 'A concise, data-driven textual answer to the user query.' },  
        chartData: {  
          type: Type.OBJECT,  
          nullable: true,  
          description: 'A valid Chart.js configuration object if the query is best represented visually (e.g., trends, comparisons). Otherwise, null.',  
          properties: {  
            type: { type: Type.STRING, description: "e.g., 'bar', 'line'" },  
            data: {  
              type: Type.OBJECT,  
              properties: {  
                labels: { type: Type.ARRAY, items: { type: Type.STRING } },  
                datasets: {  
                  type: Type.ARRAY,  
                  items: {  
                    type: Type.OBJECT,  
                    properties: {  
                      label: { type: Type.STRING },  
                      data: { type: Type.ARRAY, items: { type: Type.NUMBER } },  
                      backgroundColor: { type: Type.ARRAY, items: { type: Type.STRING } },  
                      borderColor: { type: Type.STRING },  
                      borderWidth: { type: Type.NUMBER },  
                      pointBackgroundColor: { type: Type.STRING },  
                      tension: { type: Type.NUMBER },  
                      fill: { type: Type.BOOLEAN },  
                    },  
                  },  
                },  
              },  
            },  
            options: {  
              type: Type.OBJECT,  
              nullable: true,  
              description: 'Optional Chart.js options. See Chart.js v4 documentation.',  
              properties: {  
                responsive: { type: Type.BOOLEAN, nullable: true },  
                maintainAspectRatio: { type: Type.BOOLEAN, nullable: true },  
                scales: {  
                  type: Type.OBJECT,  
                  nullable: true,  
                  properties: {  
                    y: {  
                      type: Type.OBJECT,  
                      nullable: true,  
                      properties: {  
                        beginAtZero: { type: Type.BOOLEAN, nullable: true }  
                      }  
                    }  
                  }  
                }  
              }  
            },  
          },  
        },  
      },  
    };

    try {  
      const response \= await ai.models.generateContent({  
        model: 'gemini-2.5-flash',  
        contents: prompt,  
        config: {  
          responseMimeType: 'application/json',  
          responseSchema: responseSchema  
        }  
      });  
      const parsed \= JSON.parse(response.text);  
      return parsed;  
    } catch (e) {  
      console.error("Gemini API call failed:", e);  
      return { summary: "Sorry, I encountered an error while analyzing the data.", chartData: null };  
    }  
  }

  private gatherContextualData(query: string, game: GameModel | null, allPlayers: Player\[\]): GameLog\[\] {  
    const lowerQuery \= query.toLowerCase();  
    let logs: GameLog\[\] \= \[\];

    // If game context exists, prioritize players and teams from that game  
    if (game) {  
      const teams \= \[game.homeTeam, game.awayTeam\];  
      for (const team of teams) {  
        if (lowerQuery.includes(team.toLowerCase())) {  
          logs \= \[...logs, ...this.historyService.getTeamLogs(team)\];  
        }  
      }  
      for (const player of allPlayers) {  
        const lastName \= player.name.split(' ').pop()?.toLowerCase();  
        if (lastName && lowerQuery.includes(lastName)) {  
          logs \= \[...logs, ...this.historyService.getPlayerHistory(player.name)\];  
        }  
      }  
      // If no specific entity mentioned, use all logs from the game  
      if (logs.length \=== 0\) {  
        logs \= \[...this.historyService.getTeamLogs(game.homeTeam), ...this.historyService.getTeamLogs(game.awayTeam)\];  
      }  
    } else {  
      // No game context, search all players in DB  
      const allPlayerNames \= Array.from(this.historyService.getPlayerLogsMap().keys());  
      for (const playerName of allPlayerNames) {  
        // FIX: Add type guard to ensure playerName is a string before calling toLowerCase.  
        // This resolves a type inference issue where playerName could be 'unknown'.  
        if (typeof playerName \=== 'string' && lowerQuery.includes(playerName.toLowerCase())) {  
          logs \= \[...logs, ...this.historyService.getPlayerHistory(playerName)\];  
        }  
      }  
    }

    // Fallback if no specific data is found  
    if (logs.length \=== 0\) {  
      const allDbLogs \= this.historyService.db();  
      logs \= \[...allDbLogs\].sort((a,b) \=\> new Date(b.GAME\_DATE).getTime() \- new Date(a.GAME\_DATE).getTime()).slice(0, 200);  
    }  
      
    const uniqueLogs \= Array.from(new Map(logs.map(log \=\> \[log.GAME\_ID \+ log.PLAYER\_ID, log\])).values());  
    uniqueLogs.sort((a, b) \=\> new Date(b.GAME\_DATE).getTime() \- new Date(a.GAME\_DATE).getTime());  
    return uniqueLogs.slice(0, 200);  
  }

  private constructPrompt(query: string, game: GameModel | null, relevantLogs: GameLog\[\]): string {  
    const gameContextBlock \= game  
      ? \`  
      \---  
      CONTEXT: CURRENT GAME  
      ${JSON.stringify({ matchup: \`${game.awayTeam} @ ${game.homeTeam}\`, spread: game.spread, total: game.total, date: game.date }, null, 2)}  
      \---  
      \`  
      : '';

    return \`  
      You are Ludi Lens, an expert sports betting analyst AI. Your task is to answer a user's question by analyzing the provided JSON data.  
      1\. Provide a concise, data-driven summary in the 'summary' field. Use Markdown for formatting.  
      2\. If the query involves a trend over time, a distribution, or a comparison (e.g., "last 10 games", "points distribution", "compare player stats"), you MUST generate a valid Chart.js v4 configuration object in the 'chartData' field. If a chart is not relevant, return null for 'chartData'.  
      3\. Your entire response MUST be based ONLY on the data provided.

      \*\*Charting Guidelines:\*\*  
      \- For trends (e.g., "last 10 games"), use a 'bar' chart.  
      \- Use colors that match a dark theme: backgrounds like 'rgba(75, 192, 192, 0.2)', borders like 'rgba(75, 192, 192, 1)'. For prop lines, use a 'line' type dataset with a distinct color like 'rgba(255, 99, 132, 1)'.  
      \- Keep charts simple and clear. The goal is rapid insight.  
      \- Make sure labels are concise (e.g., 'vs DEN', 'vs PHI').  
      \- Options should be minimal, but ensure ticks for y-axis are suggested (e.g. { scales: { y: { beginAtZero: true } } }).  
      \- Data must be derived directly from the historical logs provided.

      ${gameContextBlock}  
      CONTEXT: HISTORICAL GAME LOGS  
      ${JSON.stringify(relevantLogs, null, 2)}  
      \---

      QUESTION:  
      Based ONLY on the data provided, answer this question: "${query}"  
    \`;  
  }  
}  
// \--- END OF FILE src/services/lens.service.ts \---

// \--- START OF FILE src/services/model-data.service.ts \---  
import { Injectable, signal, inject } from '@angular/core';  
import { GoogleGenAI } from '@google/genai';  
import { ConfigService } from './config.service';  
import { HistoryService } from './history.service';  
import { HistorianService } from './historian.service';  
import { ZebraService } from './zebra.service';  
import { OddsService, PlayerProp } from './odds.service';  
import { ScenarioService } from './scenario.service'; // Module X  
import { YakService } from './yak.service'; // Module D  
import { CalibratorService } from './calibrator.service'; // Module E  
import { GameLog } from '../data/history-data';

export interface Player {  
  id: string;  
  name: string;  
  position: string;  
  teamAbbr: string;   
  status: 'Active' | 'Out' | 'Questionable' | 'Doubtful' | 'Minutes Limit';  
  stats: {  
    season: { pts: number, reb: number, ast: number, min: number, fga: number, fgm: number, stl: number, blk: number, tov: number, oreb: number, dreb: number, fta?: number, fg3a?: number, fantasyPts?: number, fg3m?: number };  
    l20: { pts: number, reb: number, ast: number, min: number, fga: number, fgm: number, stl: number, blk: number, tov: number, oreb: number, dreb: number, fg3m?: number, fta?: number, fg3a?: number, fantasyPts?: number };  
    l5: { pts: number, reb: number, ast: number, min: number, fga: number, fgm: number, stl: number, blk: number, tov: number, oreb: number, dreb: number, fta?: number, fg3a?: number, fantasyPts?: number, fg3m?: number };  
  };  
  props?: PlayerProp\[\];  
  // Scenario properties  
  isOut?: boolean;  
  projected?: { pts: number, reb: number, ast: number, min: number, fga?: number, fgm?: number, fg3m?: number, fta?: number, oreb?: number, dreb?: number, tov?: number, stl?: number, blk?: number, fg3a?: number, fantasyPts?: number };  
  // Module E properties  
  primaryPlayType?: string;  
  calibrationNotes?: string;  
}

export interface GameModel {  
  id: string;  
  homeTeam: string;  
  awayTeam: string;  
  date: string;  
  time: string;  
  spread: number;  
  total: number;  
  publicMoney: number;  
  sharpMoney: number;   
  yak: string;   
  refereeCrew: string\[\];   
  refereeImpact: number;   
  simResults: {  
    preYak: { homeWin: number, predictedTotal: number, homeScore: number, awayScore: number } | null;  
    postYak: { homeWin: number, predictedTotal: number, homeScore: number, awayScore: number } | null;  
  };  
  homeRoster: Player\[\];  
  awayRoster: Player\[\];  
  detailsLoaded: boolean;   
}

@Injectable({  
  providedIn: 'root'  
})  
export class ModelDataService {  
  private configService \= inject(ConfigService);  
  private historyService \= inject(HistoryService);  
  private historianService \= inject(HistorianService);  
  private zebraService \= inject(ZebraService);  
  private oddsService \= inject(OddsService);  
  private scenarioService \= inject(ScenarioService);   
  private yakService \= inject(YakService);  
  private calibratorService \= inject(CalibratorService);

  // Default Mock Data (Fallback)  
  private readonly FALLBACK\_GAMES: GameModel\[\] \= \[  
    {  
      id: 'mock\_1\_lal\_gsw',  
      homeTeam: 'GSW',  
      awayTeam: 'LAL',  
      date: '2025-12-25',  
      time: '20:00 ET',  
      spread: 2.5,  
      total: 235.5,  
      publicMoney: 75,  
      sharpMoney: 25,  
      yak: 'MOCK DATA: Christmas Day Slate. Live fetch failed (API Quota Exceeded). This is a simulated game.',  
      refereeCrew: \['Scott Foster', 'Tony Brothers', 'Sean Wright'\],  
      refereeImpact: 0.97,  
      simResults: { preYak: null, postYak: null },  
      homeRoster: \[  
         { id: 'GSW\_201939', name: 'Stephen Curry', position: 'PG', teamAbbr: 'GSW', status: 'Active', stats: { season: { pts: 29, reb: 5, ast: 6, min: 34, fga: 22, fgm: 11, stl: 1, blk: 0, tov: 3, oreb: 1, dreb: 4, fta: 5, fg3a: 11, fantasyPts: 58 }, l20: { pts: 30, reb: 5, ast: 7, min: 35, fga: 23, fgm: 12, stl: 2, blk: 0, tov: 3, oreb: 1, dreb: 4, fg3m: 4.8, fta: 5, fg3a: 11, fantasyPts: 60 }, l5: { pts: 35, reb: 4, ast: 5, min: 36, fga: 25, fgm: 14, stl: 2, blk: 0, tov: 2, oreb: 0, dreb: 4, fta: 6, fg3a: 13, fantasyPts: 65 } } },  
         { id: 'GSW\_202691', name: 'Klay Thompson', position: 'SG', teamAbbr: 'GSW', status: 'Active', stats: { season: { pts: 18, reb: 4, ast: 2, min: 32, fga: 16, fgm: 7, stl: 1, blk: 0, tov: 1, oreb: 0, dreb: 4, fta: 0, fg3a: 10, fantasyPts: 29 }, l20: { pts: 18, reb: 4, ast: 2, min: 32, fga: 16, fgm: 7, stl: 1, blk: 0, tov: 1, oreb: 0, dreb: 4, fg3m: 4.0, fta: 0, fg3a: 10, fantasyPts: 29 }, l5: { pts: 15, reb: 5, ast: 3, min: 31, fga: 14, fgm: 6, stl: 1, blk: 1, tov: 1, oreb: 1, dreb: 4, fta: 0, fg3a: 8, fantasyPts: 30.75 } } },  
         { id: 'GSW\_203110', name: 'Draymond Green', position: 'PF', teamAbbr: 'GSW', status: 'Active', stats: { season: { pts: 9, reb: 7, ast: 6, min: 28, fga: 7, fgm: 3, stl: 1, blk: 1, tov: 3, oreb: 2, dreb: 5, fta: 2, fg3a: 1, fantasyPts: 30 }, l20: { pts: 9, reb: 7, ast: 6, min: 28, fga: 7, fgm: 3, stl: 1, blk: 1, tov: 3, oreb: 2, dreb: 5, fg3m: 0.5, fta: 2, fg3a: 1, fantasyPts: 30 }, l5: { pts: 10, reb: 8, ast: 7, min: 30, fga: 8, fgm: 4, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 6, fta: 2, fg3a: 1, fantasyPts: 35 } } },  
         { id: 'GSW\_203952', name: 'Andrew Wiggins', position: 'SF', teamAbbr: 'GSW', status: 'Active', stats: { season: { pts: 15, reb: 6, ast: 2, min: 31, fga: 13, fgm: 6, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 4, fta: 2, fg3a: 4, fantasyPts: 31.2 }, l20: { pts: 15, reb: 6, ast: 2, min: 31, fga: 13, fgm: 6, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 4, fg3m: 1.0, fta: 2, fg3a: 4, fantasyPts: 31.2 }, l5: { pts: 15, reb: 6, ast: 2, min: 31, fga: 13, fgm: 6, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 4, fta: 3, fg3a: 4, fantasyPts: 31.2 } } },  
         { id: 'GSW\_1630228', name: 'Jonathan Kuminga', position: 'PF', teamAbbr: 'GSW', status: 'Active', stats: { season: { pts: 16, reb: 5, ast: 2, min: 25, fga: 12, fgm: 6, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 4, fta: 3, fg3a: 2, fantasyPts: 28 }, l20: { pts: 16, reb: 5, ast: 2, min: 25, fga: 12, fgm: 6, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 4, fg3m: 0.8, fta: 3, fg3a: 2, fantasyPts: 28 }, l5: { pts: 18, reb: 6, ast: 3, min: 28, fga: 14, fgm: 7, stl: 1, blk: 1, tov: 1, oreb: 2, dreb: 4, fta: 4, fg3a: 3, fantasyPts: 35 } } },  
         { id: 'GSW\_101108', name: 'Chris Paul', position: 'PG', teamAbbr: 'GSW', status: 'Active', stats: { season: { pts: 9, reb: 4, ast: 7, min: 26, fga: 8, fgm: 3, stl: 1, blk: 0, tov: 1, oreb: 0, dreb: 4, fta: 1, fg3a: 3, fantasyPts: 25 }, l20: { pts: 9, reb: 4, ast: 7, min: 26, fga: 8, fgm: 3, stl: 1, blk: 0, tov: 1, oreb: 0, dreb: 4, fg3m: 1.2, fta: 1, fg3a: 3, fantasyPts: 25 }, l5: { pts: 8, reb: 3, ast: 8, min: 25, fga: 7, fgm: 3, stl: 2, blk: 0, tov: 1, oreb: 0, dreb: 3, fta: 1, fg3a: 2, fantasyPts: 28 } } },  
      \],  
      awayRoster: \[  
        { id: 'LAL\_2544', name: 'LeBron James', position: 'SF', teamAbbr: 'LAL', status: 'Active', stats: { season: { pts: 25, reb: 8, ast: 8, min: 35, fga: 20, fgm: 10, stl: 1, blk: 1, tov: 3, oreb: 1, dreb: 7, fta: 6, fg3a: 5, fantasyPts: 50 }, l20: { pts: 26, reb: 9, ast: 9, min: 36, fga: 21, fgm: 11, stl: 1, blk: 1, tov: 3, oreb: 1, dreb: 8, fg3m: 2.2, fta: 6, fg3a: 5, fantasyPts: 52 }, l5: { pts: 28, reb: 8, ast: 10, min: 38, fga: 22, fgm: 12, stl: 2, blk: 1, tov: 2, oreb: 1, dreb: 7, fta: 7, fg3a: 6, fantasyPts: 55 } } },  
        { id: 'LAL\_203076', name: 'Anthony Davis', position: 'C', teamAbbr: 'LAL', status: 'Questionable', stats: { season: { pts: 24, reb: 12, ast: 3, min: 34, fga: 18, fgm: 9, stl: 1, blk: 2, tov: 2, oreb: 3, dreb: 9, fta: 5, fg3a: 1, fantasyPts: 45 }, l20: { pts: 22, reb: 11, ast: 2, min: 32, fga: 17, fgm: 8, stl: 1, blk: 2, tov: 2, oreb: 3, dreb: 8, fg3m: 0.5, fta: 5, fg3a: 1, fantasyPts: 42 }, l5: { pts: 27, reb: 15, ast: 2, min: 36, fga: 19, fgm: 11, stl: 2, blk: 2, tov: 1, oreb: 5, dreb: 10, fta: 5, fg3a: 2, fantasyPts: 58.25 } } },  
        { id: 'LAL\_1629637', name: 'D\\'Angelo Russell', position: 'PG', teamAbbr: 'LAL', status: 'Active', stats: { season: { pts: 18, reb: 3, ast: 6, min: 32, fga: 15, fgm: 7, stl: 1, blk: 0, tov: 2, oreb: 0, dreb: 3, fta: 2, fg3a: 7, fantasyPts: 32 }, l20: { pts: 18, reb: 3, ast: 6, min: 32, fga: 15, fgm: 7, stl: 1, blk: 0, tov: 2, oreb: 0, dreb: 3, fg3m: 2.8, fta: 2, fg3a: 7, fantasyPts: 32 }, l5: { pts: 20, reb: 3, ast: 7, min: 34, fga: 16, fgm: 8, stl: 1, blk: 0, tov: 2, oreb: 0, dreb: 3, fta: 2, fg3a: 8, fantasyPts: 35 } } },  
        { id: 'LAL\_1628378', name: 'Austin Reaves', position: 'SG', teamAbbr: 'LAL', status: 'Active', stats: { season: { pts: 16, reb: 4, ast: 5, min: 31, fga: 12, fgm: 6, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 3, fta: 3, fg3a: 4, fantasyPts: 28 }, l20: { pts: 16, reb: 4, ast: 5, min: 31, fga: 12, fgm: 6, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 3, fg3m: 1.5, fta: 3, fg3a: 4, fantasyPts: 28 }, l5: { pts: 15, reb: 5, ast: 6, min: 33, fga: 11, fgm: 5, stl: 1, blk: 0, tov: 1, oreb: 1, dreb: 4, fta: 4, fg3a: 4, fantasyPts: 30 } } },  
        { id: 'LAL\_1629060', name: 'Rui Hachimura', position: 'PF', teamAbbr: 'LAL', status: 'Active', stats: { season: { pts: 13, reb: 4, ast: 1, min: 25, fga: 10, fgm: 5, stl: 0, blk: 0, tov: 1, oreb: 1, dreb: 3, fta: 2, fg3a: 3, fantasyPts: 20 }, l20: { pts: 13, reb: 4, ast: 1, min: 25, fga: 10, fgm: 5, stl: 0, blk: 0, tov: 1, oreb: 1, dreb: 3, fg3m: 1.2, fta: 2, fg3a: 3, fantasyPts: 20 }, l5: { pts: 14, reb: 5, ast: 1, min: 27, fga: 11, fgm: 6, stl: 1, blk: 0, tov: 1, oreb: 2, dreb: 3, fta: 1, fg3a: 3, fantasyPts: 25 } } },  
      \],  
      detailsLoaded: true  
    },  
    {  
      id: 'mock\_2\_det\_mia',  
      homeTeam: 'MIA',  
      awayTeam: 'DET',  
      date: '2025-12-25',  
      time: '19:30 ET',  
      spread: \-5.5,  
      total: 228.0,  
      publicMoney: 60,  
      sharpMoney: 40,  
      yak: 'MOCK DATA: Live fetch failed. This is a simulated game.',  
      refereeCrew: \['Zach Zarba', 'James Williams', 'Phenizee Ransom'\],  
      refereeImpact: 1.02,  
      simResults: { preYak: null, postYak: null },  
      homeRoster: \[  
        { id: 'MIA\_202710', name: 'Jimmy Butler', position: 'SF', teamAbbr: 'MIA', status: 'Active', stats: { season: { pts: 21, reb: 5, ast: 5, min: 34, fga: 14, fgm: 7, stl: 2, blk: 0, tov: 2, oreb: 2, dreb: 3, fta: 6, fg3a: 2, fantasyPts: 40 }, l20: { pts: 21, reb: 5, ast: 5, min: 34, fga: 14, fgm: 7, stl: 2, blk: 0, tov: 2, oreb: 2, dreb: 3, fg3m: 0.8, fta: 6, fg3a: 2, fantasyPts: 40 }, l5: { pts: 23, reb: 6, ast: 6, min: 35, fga: 15, fgm: 8, stl: 2, blk: 1, tov: 1, oreb: 2, dreb: 4, fta: 7, fg3a: 2, fantasyPts: 48 } } },  
        { id: 'MIA\_1628389', name: 'Bam Adebayo', position: 'C', teamAbbr: 'MIA', status: 'Active', stats: { season: { pts: 19, reb: 10, ast: 4, min: 34, fga: 15, fgm: 8, stl: 1, blk: 1, tov: 3, oreb: 3, dreb: 7, fta: 4, fg3a: 0, fantasyPts: 40 }, l20: { pts: 19, reb: 10, ast: 4, min: 34, fga: 15, fgm: 8, stl: 1, blk: 1, tov: 3, oreb: 3, dreb: 7, fg3m: 0.1, fta: 4, fg3a: 0, fantasyPts: 40 }, l5: { pts: 20, reb: 11, ast: 3, min: 35, fga: 16, fgm: 9, stl: 1, blk: 1, tov: 2, oreb: 4, dreb: 7, fta: 3, fg3a: 0, fantasyPts: 45 } } },  
        { id: 'MIA\_1629011', name: 'Tyler Herro', position: 'SG', teamAbbr: 'MIA', status: 'Active', stats: { season: { pts: 21, reb: 5, ast: 4, min: 33, fga: 18, fgm: 8, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 4, fta: 3, fg3a: 8, fantasyPts: 35 }, l20: { pts: 21, reb: 5, ast: 4, min: 33, fga: 18, fgm: 8, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 4, fg3m: 3.5, fta: 3, fg3a: 8, fantasyPts: 35 }, l5: { pts: 22, reb: 5, ast: 5, min: 34, fga: 19, fgm: 9, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 4, fta: 2, fg3a: 9, fantasyPts: 38 } } },  
        { id: 'MIA\_1631206', name: 'Jaime Jaquez Jr.', position: 'SF', teamAbbr: 'MIA', status: 'Active', stats: { season: { pts: 19, reb: 7, ast: 3, min: 33, fga: 14, fgm: 7, stl: 1, blk: 0, tov: 1, oreb: 2, dreb: 5, fta: 5, fg3a: 4, fantasyPts: 35.9 }, l20: { pts: 19, reb: 7, ast: 3, min: 33, fga: 14, fgm: 7, stl: 1, blk: 0, tov: 1, oreb: 2, dreb: 5, fg3m: 1, fta: 5, fg3a: 4, fantasyPts: 35.9 }, l5: { pts: 19, reb: 7, ast: 3, min: 33, fga: 14, fgm: 7, stl: 1, blk: 0, tov: 1, oreb: 2, dreb: 5, fta: 5, fg3a: 4, fantasyPts: 35.9 } } },  
        { id: 'MIA\_203932', name: 'Duncan Robinson', position: 'SG', teamAbbr: 'MIA', status: 'Active', stats: { season: { pts: 15, reb: 3, ast: 2, min: 28, fga: 10, fgm: 5, stl: 1, blk: 0, tov: 1, oreb: 0, dreb: 3, fta: 0, fg3a: 10, fantasyPts: 25.6 }, l20: { pts: 15, reb: 3, ast: 2, min: 28, fga: 10, fgm: 5, stl: 1, blk: 0, tov: 1, oreb: 0, dreb: 3, fg3m: 5, fta: 0, fg3a: 10, fantasyPts: 25.6 }, l5: { pts: 15, reb: 3, ast: 2, min: 28, fga: 10, fgm: 5, stl: 1, blk: 0, tov: 1, oreb: 0, dreb: 3, fta: 0, fg3a: 10, fantasyPts: 25.6 } } }  
      \],  
      awayRoster: \[  
        { id: 'DET\_1630595', name: 'Cade Cunningham', position: 'PG', teamAbbr: 'DET', status: 'Active', stats: { season: { pts: 22, reb: 6, ast: 8, min: 34, fga: 19, fgm: 8, stl: 1, blk: 0, tov: 4, oreb: 1, dreb: 5, fta: 4, fg3a: 7, fantasyPts: 41.2 }, l20: { pts: 22, reb: 6, ast: 8, min: 34, fga: 19, fgm: 8, stl: 1, blk: 0, tov: 4, oreb: 1, dreb: 5, fg3m: 2, fta: 4, fg3a: 7, fantasyPts: 41.2 }, l5: { pts: 22, reb: 6, ast: 8, min: 34, fga: 19, fgm: 8, stl: 1, blk: 0, tov: 4, oreb: 1, dreb: 5, fta: 4, fg3a: 7, fantasyPts: 41.2 } } },  
        { id: 'DET\_1631093', name: 'Jaden Ivey', position: 'SG', teamAbbr: 'DET', status: 'Active', stats: { season: { pts: 18, reb: 4, ast: 4, min: 30, fga: 15, fgm: 7, stl: 2, blk: 0, tov: 3, oreb: 0, dreb: 4, fta: 3, fg3a: 6, fantasyPts: 31.8 }, l20: { pts: 18, reb: 4, ast: 4, min: 30, fga: 15, fgm: 7, stl: 2, blk: 0, tov: 3, oreb: 0, dreb: 4, fg3m: 2, fta: 3, fg3a: 6, fantasyPts: 31.8 }, l5: { pts: 18, reb: 4, ast: 4, min: 30, fga: 15, fgm: 7, stl: 2, blk: 0, tov: 3, oreb: 0, dreb: 4, fta: 3, fg3a: 6, fantasyPts: 31.8 } } },  
        { id: 'DET\_1630589', name: 'Ausar Thompson', position: 'SF', teamAbbr: 'DET', status: 'Active', stats: { season: { pts: 12, reb: 8, ast: 3, min: 32, fga: 11, fgm: 5, stl: 2, blk: 2, tov: 2, oreb: 3, dreb: 5, fta: 2, fg3a: 3, fantasyPts: 36.6 }, l20: { pts: 12, reb: 8, ast: 3, min: 32, fga: 11, fgm: 5, stl: 2, blk: 2, tov: 2, oreb: 3, dreb: 5, fg3m: 1, fta: 2, fg3a: 3, fantasyPts: 36.6 }, l5: { pts: 12, reb: 8, ast: 3, min: 32, fga: 11, fgm: 5, stl: 2, blk: 2, tov: 2, oreb: 3, dreb: 5, fta: 2, fg3a: 3, fantasyPts: 36.6 } } },  
        { id: 'DET\_1630166', name: 'Jalen Duren', position: 'C', teamAbbr: 'DET', status: 'Active', stats: { season: { pts: 14, reb: 12, ast: 2, min: 30, fga: 9, fgm: 6, stl: 1, blk: 1, tov: 2, oreb: 4, dreb: 8, fta: 3, fg3a: 0, fantasyPts: 36 }, l20: { pts: 14, reb: 12, ast: 2, min: 30, fga: 9, fgm: 6, stl: 1, blk: 1, tov: 2, oreb: 4, dreb: 8, fg3m: 0, fta: 3, fg3a: 0, fantasyPts: 36 }, l5: { pts: 15, reb: 13, ast: 3, min: 32, fga: 10, fgm: 7, stl: 1, blk: 1, tov: 2, oreb: 5, dreb: 8, fta: 2, fg3a: 0, fantasyPts: 40 } } },  
      \],  
      detailsLoaded: true  
    },  
    {  
      id: 'mock\_3\_lac\_sac',  
      homeTeam: 'SAC',  
      awayTeam: 'LAC',  
      date: '2025-12-25',  
      time: '22:30 ET',  
      spread: 1.5,  
      total: 231.0,  
      publicMoney: 45,  
      sharpMoney: 55,  
      yak: 'MOCK DATA: Live fetch failed. This is a simulated game.',  
      refereeCrew: \['Ed Malloy', 'Bill Kennedy', 'Andy Nagy'\],  
      refereeImpact: 1.023,  
      simResults: { preYak: null, postYak: null },  
      homeRoster: \[  
        { id: 'SAC\_1628368', name: 'De\\'Aaron Fox', position: 'PG', teamAbbr: 'SAC', status: 'Active', stats: { season: { pts: 27, reb: 4, ast: 6, min: 36, fga: 21, fgm: 10, stl: 2, blk: 0, tov: 3, oreb: 1, dreb: 3, fta: 6, fg3a: 7, fantasyPts: 45 }, l20: { pts: 27, reb: 4, ast: 6, min: 36, fga: 21, fgm: 10, stl: 2, blk: 0, tov: 3, oreb: 1, dreb: 3, fg3m: 2.5, fta: 6, fg3a: 7, fantasyPts: 45 }, l5: { pts: 29, reb: 5, ast: 7, min: 37, fga: 22, fgm: 11, stl: 2, blk: 0, tov: 2, oreb: 1, dreb: 4, fta: 7, fg3a: 8, fantasyPts: 50 } } },  
        { id: 'SAC\_1627734', name: 'Domantas Sabonis', position: 'C', teamAbbr: 'SAC', status: 'Active', stats: { season: { pts: 20, reb: 13, ast: 8, min: 36, fga: 14, fgm: 8, stl: 1, blk: 1, tov: 4, oreb: 4, dreb: 9, fta: 5, fg3a: 1, fantasyPts: 50 }, l20: { pts: 20, reb: 13, ast: 8, min: 36, fga: 14, fgm: 8, stl: 1, blk: 1, tov: 4, oreb: 4, dreb: 9, fg3m: 0.5, fta: 5, fg3a: 1, fantasyPts: 50 }, l5: { pts: 21, reb: 14, ast: 9, min: 37, fga: 15, fgm: 9, stl: 1, blk: 1, tov: 3, oreb: 4, dreb: 10, fta: 4, fg3a: 1, fantasyPts: 55 } } },  
        { id: 'SAC\_1630559', name: 'Davion Mitchell', position: 'PG', teamAbbr: 'SAC', status: 'Active', stats: { season: { pts: 8, reb: 2, ast: 4, min: 22, fga: 8, fgm: 3, stl: 2, blk: 0, tov: 2, oreb: 0, dreb: 2, fta: 1, fg3a: 4, fantasyPts: 18.4 }, l20: { pts: 8, reb: 2, ast: 4, min: 22, fga: 8, fgm: 3, stl: 2, blk: 0, tov: 2, oreb: 0, dreb: 2, fg3m: 1, fta: 1, fg3a: 4, fantasyPts: 18.4 }, l5: { pts: 8, reb: 2, ast: 4, min: 22, fga: 8, fgm: 3, stl: 2, blk: 0, tov: 2, oreb: 0, dreb: 2, fta: 1, fg3a: 4, fantasyPts: 18.4 } } }  
      \],  
      awayRoster: \[  
         { id: 'LAC\_202695', name: 'Kawhi Leonard', position: 'SF', teamAbbr: 'LAC', status: 'Active', stats: { season: { pts: 24, reb: 6, ast: 4, min: 34, fga: 18, fgm: 9, stl: 2, blk: 1, tov: 2, oreb: 1, dreb: 5, fta: 5, fg3a: 4, fantasyPts: 42 }, l20: { pts: 24, reb: 6, ast: 4, min: 34, fga: 18, fgm: 9, stl: 2, blk: 1, tov: 2, oreb: 1, dreb: 5, fg3m: 2, fta: 5, fg3a: 4, fantasyPts: 42 }, l5: { pts: 26, reb: 7, ast: 4, min: 35, fga: 19, fgm: 10, stl: 2, blk: 1, tov: 1, oreb: 1, dreb: 6, fta: 5, fg3a: 4, fantasyPts: 48 } } },  
         { id: 'LAC\_202331', name: 'Norman Powell', position: 'SG', teamAbbr: 'LAC', status: 'Active', stats: { season: { pts: 17, reb: 3, ast: 1, min: 25, fga: 12, fgm: 6, stl: 1, blk: 0, tov: 1, oreb: 1, dreb: 2, fta: 2, fg3a: 7, fantasyPts: 24.1 }, l20: { pts: 17, reb: 3, ast: 1, min: 25, fga: 12, fgm: 6, stl: 1, blk: 0, tov: 1, oreb: 1, dreb: 2, fg3m: 3, fta: 2, fg3a: 7, fantasyPts: 24.1 }, l5: { pts: 17, reb: 3, ast: 1, min: 25, fga: 12, fgm: 6, stl: 1, blk: 0, tov: 1, oreb: 1, dreb: 2, fta: 2, fg3a: 7, fantasyPts: 24.1 } } }  
      \],  
      detailsLoaded: true  
    },  
     {  
      id: 'mock\_4\_phi\_bos',  
      homeTeam: 'BOS',  
      awayTeam: 'PHI',  
      date: '2025-12-25',  
      time: '17:00 ET',  
      spread: \-8.0,  
      total: 225.5,  
      publicMoney: 80,  
      sharpMoney: 20,  
      yak: 'MOCK DATA: Live fetch failed. This is a simulated game.',  
      refereeCrew: \['Marc Davis', 'Courtney Kirkland', 'John Goble'\],  
      refereeImpact: 0.99,  
      simResults: { preYak: null, postYak: null },  
      homeRoster: \[  
        { id: 'BOS\_1628369', name: 'Jayson Tatum', position: 'SF', teamAbbr: 'BOS', status: 'Active', stats: { season: { pts: 27, reb: 8, ast: 5, min: 36, fga: 20, fgm: 9, stl: 1, blk: 1, tov: 3, oreb: 1, dreb: 7, fta: 7, fg3a: 8, fantasyPts: 48 }, l20: { pts: 27, reb: 8, ast: 5, min: 36, fga: 20, fgm: 9, stl: 1, blk: 1, tov: 3, oreb: 1, dreb: 7, fg3m: 3, fta: 7, fg3a: 8, fantasyPts: 48 }, l5: { pts: 28, reb: 9, ast: 6, min: 37, fga: 21, fgm: 10, stl: 1, blk: 1, tov: 2, oreb: 1, dreb: 8, fta: 8, fg3a: 8, fantasyPts: 52 } } },  
        { id: 'BOS\_203935', name: 'Jaylen Brown', position: 'SG', teamAbbr: 'BOS', status: 'Active', stats: { season: { pts: 23, reb: 6, ast: 4, min: 34, fga: 18, fgm: 9, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 5, fta: 4, fg3a: 6, fantasyPts: 38 }, l20: { pts: 23, reb: 6, ast: 4, min: 34, fga: 18, fgm: 9, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 5, fg3m: 2.5, fta: 4, fg3a: 6, fantasyPts: 38 }, l5: { pts: 25, reb: 7, ast: 4, min: 35, fga: 19, fgm: 10, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 5, fta: 4, fg3a: 6, fantasyPts: 42 } } },  
        { id: 'BOS\_204001', name: 'Kristaps Porzingis', position: 'C', teamAbbr: 'BOS', status: 'Active', stats: { season: { pts: 20, reb: 7, ast: 2, min: 30, fga: 14, fgm: 7, stl: 1, blk: 2, tov: 2, oreb: 2, dreb: 5, fta: 5, fg3a: 5, fantasyPts: 38 }, l20: { pts: 20, reb: 7, ast: 2, min: 30, fga: 14, fgm: 7, stl: 1, blk: 2, tov: 2, oreb: 2, dreb: 5, fg3m: 2, fta: 5, fg3a: 5, fantasyPts: 38 }, l5: { pts: 18, reb: 6, ast: 2, min: 28, fga: 13, fgm: 6, stl: 0, blk: 2, tov: 2, oreb: 1, dreb: 5, fta: 4, fg3a: 4, fantasyPts: 35 } } },  
      \],  
      awayRoster: \[  
        { id: 'PHI\_203954', name: 'Joel Embiid', position: 'C', teamAbbr: 'PHI', status: 'Active', stats: { season: { pts: 33, reb: 11, ast: 6, min: 34, fga: 20, fgm: 11, stl: 1, blk: 2, tov: 4, oreb: 3, dreb: 8, fta: 12, fg3a: 3, fantasyPts: 60 }, l20: { pts: 33, reb: 11, ast: 6, min: 34, fga: 20, fgm: 11, stl: 1, blk: 2, tov: 4, oreb: 3, dreb: 8, fg3m: 1.2, fta: 12, fg3a: 3, fantasyPts: 60 }, l5: { pts: 35, reb: 12, ast: 7, min: 35, fga: 21, fgm: 12, stl: 1, blk: 2, tov: 3, oreb: 3, dreb: 9, fta: 13, fg3a: 3, fantasyPts: 68 } } },  
        { id: 'PHI\_1629001', name: 'Tyrese Maxey', position: 'PG', teamAbbr: 'PHI', status: 'Active', stats: { season: { pts: 26, reb: 4, ast: 6, min: 38, fga: 20, fgm: 9, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 3, fta: 6, fg3a: 8, fantasyPts: 42 }, l20: { pts: 26, reb: 4, ast: 6, min: 38, fga: 20, fgm: 9, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 3, fg3m: 3.2, fta: 6, fg3a: 8, fantasyPts: 42 }, l5: { pts: 28, reb: 4, ast: 7, min: 39, fga: 21, fgm: 10, stl: 1, blk: 0, tov: 2, oreb: 1, dreb: 3, fta: 7, fg3a: 9, fantasyPts: 48 } } },  
        { id: 'PHI\_1642845', name: 'VJ Edgecombe', position: 'SG', teamAbbr: 'PHI', status: 'Active', stats: { season: { pts: 26, reb: 4, ast: 7, min: 39, fga: 17, fgm: 10, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 2, fta: 4, fg3a: 4, fantasyPts: 45.3 }, l20: { pts: 26, reb: 4, ast: 7, min: 39, fga: 17, fgm: 10, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 2, fg3m: 2, fta: 4, fg3a: 4, fantasyPts: 45.3 }, l5: { pts: 26, reb: 4, ast: 7, min: 39, fga: 17, fgm: 10, stl: 1, blk: 1, tov: 2, oreb: 2, dreb: 2, fta: 4, fg3a: 4, fantasyPts: 45.3 } } }  
      \],  
      detailsLoaded: true  
    }  
  \];

  games \= signal\<GameModel\[\]\>(\[\]);  
  activeGameId \= signal\<string | null\>(null);  
  isGameLoading \= signal\<boolean\>(false);  
  systemStatus \= signal\<string\>('System Offline');

  private playerStatsCache \= signal\<Map\<number, Player\['stats'\]\>\>(new Map());

  /\*\*  
   \* MODULE 2: INITIALIZE SEASON (The Census)  
   \* Matches \`update\_stats()\` logic from Python script.  
   \*/  
  async initializeSeason() {  
    console.log(\`\\n${'='.repeat(40)}\`);  
    console.log(\`LUDI INFORMATIO: SEASON INITIALIZATION\`);  
    console.log(\`${'='.repeat(40)}\`);  
      
    const targetSeason \= this.configService.currentSeason();  
    console.log(\`\[CENSUS\] 📡 Detected Target Season: ${targetSeason}\`);  
    this.systemStatus.set(\`Census: Detected Season ${targetSeason}...\`);

    try {  
      // 1\. LOAD HISTORICAL DATABASE (STATIC FALLBACK)  
      // This step now uses the built-in static data to prevent API quota errors on startup.  
      this.systemStatus.set(\`Census: Loading Static DB...\`);  
      console.log(\`\[CENSUS\]    \> Loading historical data from static fallback to prevent API quota issues.\`);  
      const count \= this.historyService.loadFallbackDatabase();  
      console.log(\`\[CENSUS\] ✅ Loaded ${count} rows from static database.\`);  
        
      // Pre-compute all player averages for performance  
      this.\_precomputePlayerStats();  
        
      // 2\. Continue to Zebras (Module G)  
      this.systemStatus.set('Zebras: Loading Assignments...');  
      const zebraMsg \= await this.zebraService.loadAssignments();  
      console.log(zebraMsg);  
        
      // 3\. Fetch LIVE Daily Slate (Module A \- Gatekeeper)  
      this.systemStatus.set(\`Gatekeeper: Fetching Live Slate (Odds API)...\`);  
      await this.loadDailySlate();

      console.log(\`\[CENSUS\] System Ready.\`);  
      this.systemStatus.set('System Ready');  
        
    } catch (e) {  
      console.error('Failed to initialize season', e);  
      this.systemStatus.set('Census Failed');  
      this.historyService.loadFallbackDatabase();  
    }  
  }

  /\*\*  
   \* Fetches games from Odds Service (Module A) and maps them to GameModels.  
   \*/  
  private async loadDailySlate() {  
    try {  
      const liveGames \= await this.oddsService.fetchLiveSlate();  
        
      if (liveGames.length \=== 0\) {  
        console.warn('\[GATEKEEPER\] No games found on Live API. Using Fallback/Simulated Slate.');  
        this.games.set(this.FALLBACK\_GAMES);  
        return;  
      }

      const mappedGames: GameModel\[\] \= liveGames.map(g \=\> {  
        const crew \= this.zebraService.getCrew(g.homeTeam);  
        const impact \= this.zebraService.getGameImpact(g.homeTeam);  
        const splits \= this.oddsService.calculateMoneySplits(g.bookmakers);

        const timeStr \= g.commenceTime.toLocaleTimeString('en-US', {   
          hour: 'numeric', minute: '2-digit', timeZone: 'America/New\_York', timeZoneName: 'short'   
        });  
        const dateStr \= g.commenceTime.toISOString().split('T')\[0\];

        return {  
          id: g.id,  
          homeTeam: g.homeTeam,  
          awayTeam: g.awayTeam,  
          date: dateStr,  
          time: timeStr,  
          spread: g.spread || 0,  
          total: g.total || 0,  
          publicMoney: splits.public,  
          sharpMoney: splits.sharp,  
          yak: '',  
          refereeCrew: crew,  
          refereeImpact: impact,  
          simResults: { preYak: null, postYak: null },  
          homeRoster: \[\],   
          awayRoster: \[\],  
          detailsLoaded: false   
        };  
      });

      this.games.set(mappedGames);  
    } catch (e) {  
      console.error('\[GATEKEEPER\] Error loading slate', e);  
      this.games.set(this.FALLBACK\_GAMES);  
    }  
  }

  async setActiveGame(gameId: string) {  
    this.activeGameId.set(gameId);  
      
    const game \= this.games().find(g \=\> g.id \=== gameId);  
    if (\!game || game.detailsLoaded) return; 

    this.isGameLoading.set(true);  
    this.systemStatus.set(\`Loading Details for ${game.awayTeam} @ ${game.homeTeam}...\`);

    try {  
      const props \= await this.oddsService.fetchPlayerProps(gameId);  
      let tankStats: GameLog\[\] \= \[\];

      // SIMULATION HOOK: If it's a mock game, try to get a simulated box score.  
      if (game.id.startsWith('mock\_')) {  
        console.log('\[HISTORIAN\] 🎮 Using simulated box score for mock game.');  
        tankStats \= this.historianService.getSimulatedBoxScore(game.id, game.homeTeam, game.awayTeam);  
      } else {  
        // LIVE LOGIC: Fetch real data for live games  
        const gameDate \= new Date(game.date);  
        const tankGameId \= await this.historianService.findTankGameId(gameDate, game.homeTeam, game.awayTeam);  
        if (tankGameId) {  
          tankStats \= await this.historianService.getGameBoxScore(tankGameId, game.date);  
        }  
      }  
        
      const updatedGame \= { ...game, detailsLoaded: true };

      // SCENARIO 1: LIVE GAME IN PROGRESS / JUST FINISHED (OR SIMULATED FINISHED)  
      // We have an official box score. This is the source of truth.  
      if (tankStats.length \> 0\) {  
          console.log(\`\[MODEL\] Building roster from Live Box Score...\`);  
          const playerIdentities \= tankStats.map(log \=\> ({ PLAYER\_ID: log.PLAYER\_ID, PLAYER\_NAME: log.PLAYER\_NAME, TEAM\_ABBREVIATION: log.TEAM\_ABBREVIATION }));  
          const fullRoster \= playerIdentities.map(p \=\> this.buildPlayerFromCache(p));  
          updatedGame.homeRoster \= fullRoster.filter(p \=\> p.teamAbbr \=== game.homeTeam);  
          updatedGame.awayRoster \= fullRoster.filter(p \=\> p.teamAbbr \=== game.awayTeam);  
      }   
      // SCENARIO 2: PRE-GAME / API FAILURE  
      // We have no live box score. The betting props are our best source for who is expected to play.  
      else {  
          console.log('\[MODEL\] ⚠️ Live Roster API failed or pre-game. Building roster from player props and history...');  
          const { homeRoster, awayRoster } \= this.\_buildRostersFromProps(props, game.homeTeam, game.awayTeam);  
          updatedGame.homeRoster \= homeRoster;  
          updatedGame.awayRoster \= awayRoster;  
      }  
        
      // Always attach props to the final rosters  
      updatedGame.homeRoster \= this.attachPropsToRoster(updatedGame.homeRoster, props);  
      updatedGame.awayRoster \= this.attachPropsToRoster(updatedGame.awayRoster, props);  
        
      this.updateGameInState(updatedGame);  
      this.systemStatus.set('System Ready');

    } catch (e) {  
      console.error('Error loading game details', e);  
      this.systemStatus.set('Partial Data Load');  
    } finally {  
      this.isGameLoading.set(false);  
    }  
  }

  // \--- HELPERS \---

  private \_buildRostersFromProps(props: PlayerProp\[\], homeTeam: string, awayTeam: string): { homeRoster: Player\[\], awayRoster: Player\[\] } {  
    const homeRoster: Player\[\] \= \[\];  
    const awayRoster: Player\[\] \= \[\];  
    const ghostPlayers: Player\[\] \= \[\];  
    const uniqueNames \= \[...new Set(props.map(p \=\> p.playerName))\];

    for (const name of uniqueNames) {  
        const playerLogs \= this.historyService.getPlayerHistory(name);  
          
        if (playerLogs.length \> 0\) {  
            // Player found in history \- Primary Method  
            playerLogs.sort((a, b) \=\> new Date(b.GAME\_DATE).getTime() \- new Date(a.GAME\_DATE).getTime());  
            const mostRecentLog \= playerLogs\[0\];  
            const teamAbbr \= mostRecentLog.TEAM\_ABBREVIATION;

            // Only add if their last known team is playing today  
            if (teamAbbr \=== homeTeam || teamAbbr \=== awayTeam) {