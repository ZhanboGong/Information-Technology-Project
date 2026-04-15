import Cookies from 'js-cookie';

const TokenKey = 'jwt_token';
const UserKey = 'user_info';

// 获取 Token
export const getToken = () => Cookies.get(TokenKey);

// 设置 Token (1天过期)
export const setToken = (token) => {
  if (token) {
    Cookies.set(TokenKey, token, { expires: 1, path: '/' });
  }
};

// 移除 Token
export const removeToken = () => Cookies.remove(TokenKey, { path: '/' });

// 获取用户信息 (增加健壮性检查)
export const getUser = () => {
  const user = Cookies.get(UserKey);

  // 核心修复：排除 undefined 字符串和空值
  if (!user || user === 'undefined' || user === 'null') {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch (error) {
    console.error("Auth: 用户信息解析失败，正在清理异常数据", error);
    // 如果解析失败，说明数据格式不对，直接清理并返回 null
    Cookies.remove(UserKey);
    return null;
  }
};

// 设置用户信息 (确保存入的是规范的 JSON 字符串)
export const setUser = (user) => {
  if (user) {
    Cookies.set(UserKey, JSON.stringify(user), { expires: 1, path: '/' });
  }
};

// 移除用户信息
export const removeUser = () => Cookies.remove(UserKey, { path: '/' });