const getBaseURL = () => {
  const isProd = import.meta.env.PROD;
  return isProd ? "/api/" : "http://localhost:8000/api/";
};

export default getBaseURL;
