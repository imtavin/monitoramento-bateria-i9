document.addEventListener('DOMContentLoaded', function () {
    // --- SIDEBAR ---
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const toggleSidebar = document.getElementById('toggleSidebar');
    const footer = document.querySelector('footer');

    // Função para inicializar a sidebar
    function initializeSidebar() {
        if (window.innerWidth <= 768) {
            sidebar.classList.add('collapsed');
            if (mainContent) mainContent.classList.add('collapsed');
        } else {
            sidebar.classList.remove('collapsed');
            if (mainContent) mainContent.classList.remove('collapsed');
        }
    }

    // Executa a inicialização
    initializeSidebar();
    window.addEventListener('resize', initializeSidebar);

   // Alterna a visibilidade da sidebar ao clicar no botão
   if (toggleSidebar) {
    toggleSidebar.addEventListener('click', () => {
        sidebar.classList.toggle('active'); // Mostra/oculta a sidebar
        mainContent.classList.toggle('sidebar-active'); // Ajusta o conteúdo principal
        footer.classList.toggle('sidebar-active'); // Ajusta o rodapé
         });
    }

    toggleSidebar.addEventListener('click', () => {
        toggleSidebar.classList.toggle('sidebar-active');
         });
})