import axios from "axios";

const localUrlToBlob = async (localUrl) => {
  const response = await axios.get(localUrl, { responseType: "blob" });
  return response.data;
};

export default localUrlToBlob;
