// welcome-animation.js
// Shows the animated welcome (if present) and then reveals a persistent title in the navbar.
(function(){
  function safeJSONParse(text){ try { return JSON.parse(text); } catch(e){ return null; } }
  const dataEl = document.getElementById('page-data');
  const page = dataEl ? safeJSONParse(dataEl.textContent) : null;
  const loggedIn = page && page.logged_in === true || page && page.logged_in === 'true';
  const shouldAnimate = page && (page.show_welcome_animation === true || page.show_welcome_animation === 'true');
  const userName = page && page.user_name ? page.user_name : '';

  const animatedEl = document.querySelector('.animated-welcome-text');
  // Create persistent placeholder in navbar if not exists
  let persistent = document.querySelector('.persistent-welcome');
  if(!persistent){
    const navLinks = document.querySelector('.nav-links');
    if(navLinks){
      persistent = document.createElement('span');
      persistent.className = 'persistent-welcome';
      persistent.setAttribute('aria-hidden','true');
      persistent.textContent = userName ? `Bienvenido, ${userName}` : '';
      navLinks.insertBefore(persistent, navLinks.firstChild);
    }
  }

  function showPersistent(){
    if(persistent){
      persistent.classList.add('show');
    }
    // Update small greeting if present
    const greeting = document.querySelector('.user-greeting');
    if(greeting && userName){
      greeting.textContent = `Hola, ${userName}`;
    }
  }

  // If logged in but no animation flag (e.g., on subsequent pages), just show persistent immediately
  if(loggedIn && !shouldAnimate){
    showPersistent();
    return;
  }

  // If animation should run but was already shown earlier, skip animation and show persistent
  try{
    if(localStorage.getItem('welcomeShown')){
      showPersistent();
      return;
    }
  }catch(e){ /* ignore storage errors */ }

  if(animatedEl){
    // Ensure the animated element becomes visible (CSS animations are declared in CSS)
    // After the composed animation durations in CSS (typing 2s + subtitle + fade), show persistent
    // We'll wait 4.5s which matches the fadeOutWrapper timing in CSS
    setTimeout(function(){
      showPersistent();
      try{ localStorage.setItem('welcomeShown', '1'); }catch(e){}
      // Add docked class to the animated element to provide a visual morph briefly
      animatedEl.classList.add('docked');
      // keep animatedEl in DOM but hidden visually after transition
      setTimeout(function(){
        // Optionally hide the large element so it doesn't obstruct
        if(animatedEl.parentElement){
          animatedEl.style.opacity = '0';
          animatedEl.style.pointerEvents = 'none';
        }
      }, 700);
    }, 4500);
  }
})();
