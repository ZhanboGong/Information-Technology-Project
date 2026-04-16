import Cookies from 'js-cookie';

const TokenKey = 'jwt_token';
const UserKey = 'user_info';

// Obtain Token
export const getToken = () => Cookies.get(TokenKey);

// Set Token (expires in 1 day)
export const setToken = (token) => {
  if (token) {
    Cookies.set(TokenKey, token, { expires: 1, path: '/' });
  }
};

// Remove Token
export const removeToken = () => Cookies.remove(TokenKey, { path: '/' });

// Obtain user information
export const getUser = () => {
  const user = Cookies.get(UserKey);

  if (!user || user === 'undefined' || user === 'null') {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch (error) {
    console.error("Auth: 用户信息解析失败，正在清理异常数据", error);
    Cookies.remove(UserKey);
    return null;
  }
};

// Set user information
export const setUser = (user) => {
  if (user) {
    Cookies.set(UserKey, JSON.stringify(user), { expires: 1, path: '/' });
  }
};

// Remove user information
export const removeUser = () => Cookies.remove(UserKey, { path: '/' });