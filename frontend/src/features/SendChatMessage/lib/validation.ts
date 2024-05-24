export const validateInputFile = (file: File | undefined) => {
  return file && file.name.match(/\.(jpeg|png|mp4|pdf)$/i);
};
