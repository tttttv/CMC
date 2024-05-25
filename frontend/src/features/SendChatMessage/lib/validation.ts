export const validateInputFile = (file: File | undefined) => {
  return file && file.name.match(/\.(jpeg|jpg|png|mp4|pdf)$/i);
};
