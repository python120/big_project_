var vm = new Vue({
    el: '#app',
	// 修改Vue变量的读取语法，避免和django模板语法冲突
    delimiters: ['[[', ']]'],
    data: {
        host: host,
        username: '',
        sina_user_name: '',
        sina_img_url: '',
        profile_url: '',
        sina_before: 'http://www.weibo.com/',
    },
    mounted(){
        this.username = getCookie('username');
    },
    created: function(){
        ask_sina_msg(this);
    },

})